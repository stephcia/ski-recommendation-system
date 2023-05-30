import streamlit as st
import pandas as pd
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity
from surprise import SVDpp, SVD
from surprise import accuracy
from surprise import Dataset
from surprise import Reader
from surprise.model_selection import GridSearchCV, cross_validate, train_test_split

from PIL import Image
import plotly.express as px

#importing files
content_matrix = pd.read_csv("data/cleaned_data_exports/scraped_feature_df_3.csv")
sim_df = pd.read_csv("data/cleaned_data_exports/similarity_matrix.csv")
final_user_df = pd.read_csv("data/cleaned_data_exports/user_df_model.csv")
surprise_df = pd.read_csv("data/cleaned_data_exports/surprise_df.csv")

#resetting index
sim_df = sim_df.set_index('ski_resort')
content_matrix = content_matrix.set_index('ski_resort')

#dropping unnamed column
df_list = [content_matrix, final_user_df, surprise_df]

for x in df_list:
    x.drop(columns="Unnamed: 0", inplace=True)
    
#dropping duplicates
surprise_df = surprise_df.drop_duplicates()

#setting scale
reader = Reader(rating_scale=(1, 5))

#loading final dataset
data_full = Dataset.load_from_df(surprise_df[['user_name', 'ski_resort', 'rating']], reader)

#making trainset
full_trainset = data_full.build_full_trainset()

#saving new dataframe with only user information
user_df = surprise_df.reset_index()
user_df.set_index('user_name', inplace = True)
user_df.drop(columns = ['rating', 'index'], inplace =True)
user_df.head()

# function to load and read images
def load_image(img):
    im = Image.open(img)
    image = np.array(im)
    return image

def load_model(model_filename):
    print (">> Loading dump")
    from surprise import dump
    import os
    file_name = os.path.expanduser(model_filename)
    _, loaded_model = dump.load(file_name)
    return loaded_model

def hybrid_model_content(user, n_recs, mountain_name, travel_date, mtn_pass):
 
    loaded_model = load_model('model.pickle')
    
    # Content-based model
    y = sim_df.loc[[mountain_name]]
    cos_sim = cosine_similarity(sim_df, y)
    cos_sim_df = pd.DataFrame(data=cos_sim, index=sim_df.index)
    cos_sim_df.sort_values(by=0, ascending=False, inplace=True)
    cos_sim_df = cos_sim_df.reset_index()

    #making list for column names
    rec_list = []
    
    #grabbing rows from content_matrix for final output
    for x in cos_sim_df['ski_resort']:
        rec_df = content_matrix.loc[[x]]  
        rec_list.append(rec_df)  #

    rec_df = pd.concat(rec_list)

    #Concatenate all the dataframes in rec_list into a single dataframe
    concat_df = rec_df[["city", "state", "summit", "drop", "base","adultWeekdayPrice",
                        "adultWeekendPrice","beginner_runs", "intermediate_runs", "advanced_runs",
                        "expert_runs","ikon", "epic", "mountain_collective", 'latitude','longitude']]
    concat_df = concat_df.reset_index()

    #filtering based on month to return airbnb prices and turning into dataframe
    travel_date = travel_date.lower()

    month = ["december", "january", "february", "march", "april", "may"]
    month_abv = ["dec", "jan", "feb", "mar", "apr", "may"]

    selected_columns = []
    for x, y in zip(month_abv, month):
        if travel_date == y:
            selected_columns = [x + "_mean_4_guests", x + "_mean_2_guests"]

    result = rec_df[selected_columns]
    result = result.reset_index()                        
    content_recommendations = pd.merge(concat_df, result, on="ski_resort")
    
    #adding mountain fil
    if mtn_pass == "Ikon":
        content_recommendations = content_recommendations.loc[content_recommendations['ikon'] == 1]
    elif mtn_pass == "Epic":
        content_recommendations = content_recommendations.loc[content_recommendations['epic'] == 1]
    elif mtn_pass == "Mountain_collective":
        content_recommendations = content_recommendations.loc[content_recommendations['mountain_collective'] == 1]
    elif mtn_pass == "No":
        pass
    
    content_recommendations = content_recommendations[content_recommendations.ski_resort != mountain_name].head(20)

    # Collaborative model
    have_rated = list(user_df.loc[user, 'ski_resort'])
    not_rated = final_user_df.copy()
    not_rated = not_rated.loc[~not_rated['ski_resort'].isin(have_rated)]
    not_rated = not_rated.drop_duplicates(subset=['ski_resort'])
    not_rated.reset_index(inplace=True)
    not_rated['predicted_rating'] = not_rated['ski_resort'].apply(lambda x: loaded_model.predict(user, x).est)
    not_rated.sort_values(by='predicted_rating', ascending=False, inplace=True)
    collaborative_recommendations = not_rated[['ski_resort', 'predicted_rating']]

    # Combine content-based and collaborative recommendations
    combined_recommendations = pd.merge(content_recommendations, collaborative_recommendations, on='ski_resort', how='left')
    combined_recommendations = combined_recommendations.drop_duplicates(subset=['ski_resort'])
    combined_recommendations.sort_values(by='predicted_rating', ascending=False, inplace=True)
    combined_recommendations.drop(columns=['ikon', 'mountain_collective', 'epic'], inplace=True)
    final_recs = combined_recommendations.drop(columns=['longitude', 'latitude', 'city'])
    
    rename_list = ["ski_resort", "state","summit", "drop", "base", "adultWeekdayPrice",
                   "adultWeekendPrice", "beginner_runs",
                  "intermediate_runs", "advanced_runs",
                   "expert_runs", "dec_mean_4_guests","dec_mean_2_guests"]
                                                        
    rename_to = ["Ski Resort", "State (ft)", "Summit (ft)" , "Drop (ft)",
                "Base (ft)","Weekday Lift Ticket ($)", "Weekend Lift Ticket ($)",
                "Beginner Runs (%)", "Intermediate Runs (%)", "Advanced Runs(%)", "Expert Runs (%)",
                 "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)"]
    
    columns_dict = dict(zip(rename_list, rename_to))
    final_recs = final_recs.rename(columns=columns_dict).set_index('Ski Resort')
    return final_recs.head(n_recs).T
                 
#making a list of mountain names for input
resort_names = content_matrix.index.tolist()
month_list = ['December', 'January', 'February', 'March', 'April', 'May']
pass_list = ['Ikon', 'Epic', 'Mountain Collective', 'Indy']


# User inputs
user = st.text_input('Name')
n_recs = st.number_input('How many resort recommendations do you want?', min_value=1, step=1)
mountain_name = st.selectbox("What's your favorite ski resort?", resort_names)
travel_date = st.selectbox('What month would you like to travel?', month_list)
mtn_pass = st.radio('Are you using a multi-resort pass?', ('Yes', 'No'))
if mtn_pass == 'Yes':
    radio_choice = st.radio('Choose an option', pass_list)

# Button to trigger recommendation
if st.button("Get Recommendations"):
    # Call the hybrid model function and get recommendations
    recommendations = hybrid_model_content(user, n_recs, mountain_name, travel_date, mtn_pass)

    # Display the final recommendations
    st.subheader("Recommendations")
    st.dataframe(recommendations)

    #displaying map of ski resorts
    rec_list = recommendations.columns.to_list()
    rec_map_df = content_matrix[content_matrix.index.isin(rec_list)]
    rec_map_df = rec_map_df.reset_index()
    
#     image = Image.open('images/icons/cable-car.png')
    
#     lift_num = rec_map_df['total_lifts'][0]
#     st.image(image, caption=lift_num, width=60)
    
    fig = px.scatter_mapbox(rec_map_df, lat='latitude', lon='longitude',
                            hover_name="ski_resort", hover_data=["summit", "base",
                                                                 "drop"],
                            color_discrete_sequence=["blue"], zoom=2.5)
    
    #loop_list = range(n_recs)
    
    #for x in loop_list:
    
        #fig.add_trace(px.scatter_mapbox(rec_map_df, lat='lat', lon='long',
                                        #color_discrete_sequence=["white"]).data[x])

        #fig.add_trace(px.scatter_mapbox(rec_map_df, lat='lat_2', lon='long_2',
                                        #color_discrete_sequence=["white"]).data[x])

    # Update the map layout
    fig.update_layout(mapbox_style='open-street-map')
    fig.update_layout(margin={'r': 0, 't': 0, 'l': 0, 'b': 0})

    # Display the map
    st.plotly_chart(fig, use_container_width=True)
        
        
        
        