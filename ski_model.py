import streamlit as st
import pandas as pd
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity
from surprise import SVDpp, SVD
from surprise import accuracy
from surprise import Dataset
from surprise import Reader
from surprise.model_selection import GridSearchCV, cross_validate, train_test_split

from PIL import Image, ImageDraw, ImageFont
import plotly.express as px
import textwrap

#importing files
content_matrix = pd.read_csv("data/cleaned_data_exports/scraped_feature_df.csv")
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

@st.cache_data
def load_model(model_filename):
    print (">> Loading dump")
    from surprise import dump
    import os
    file_name = os.path.expanduser(model_filename)
    _, loaded_model = dump.load(file_name)
    return loaded_model


#making a list of mountain names for input
resort_names = content_matrix.index.tolist()
month_list = ['December', 'January', 'February', 'March', 'April', 'May']
pass_list = ['Ikon', 'Epic', 'Mountain Collective', 'Indy']

pass_column_mapping = {
    'Ikon': 'ikon',
    'Epic': 'epic',
    'Mountain Collective': 'mountain_collective',
    'Indy': 'indy'
}

def hybrid_model_content(user, n_recs, mountain_name, travel_date, mtn_pass, radio_choices):
 
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
                        "expert_runs","ikon", "epic", "indy", "mountain_collective", 'latitude','longitude']]
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
    
    
    filtered_recommendations = pd.DataFrame()
    
    for choice in radio_choices:
        column_name = pass_column_mapping.get(choice)
        if column_name and column_name in content_recommendations.columns:
            
            filtered_df = content_recommendations[content_recommendations[column_name] == 1]
            
            
            filtered_df['Pass'] = choice
            
         
            filtered_recommendations = pd.concat([filtered_recommendations, filtered_df])
    
    content_recommendations = filtered_recommendations
    
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
    combined_recommendations.drop(columns=['ikon', 'mountain_collective', 'epic', 'indy'], inplace=True)
    final_recs = combined_recommendations.drop(columns=['longitude', 'latitude', 'city'])
    
    rename_list = ["ski_resort", "state","summit", "drop", "base", "adultWeekdayPrice",
                   "adultWeekendPrice", "beginner_runs",
                  "intermediate_runs", "advanced_runs",
                   "expert_runs", "dec_mean_4_guests","dec_mean_2_guests",
                   "predicted_rating", "jan_mean_4_guests","jan_mean_2_guests", "feb_mean_4_guests","feb_mean_2_guests", "mar_mean_4_guests","mar_mean_2_guests", "apr_mean_4_guests","apr_mean_2_guests", "may_mean_4_guests","may_mean_2_guests" ]
                                                        
    rename_to = ["Ski Resort", "State", "Summit (ft)" , "Drop (ft)",
                "Base (ft)","Weekday Lift Ticket ($)", "Weekend Lift Ticket ($)",
                "Beginner Runs (%)", "Intermediate Runs (%)", "Advanced Runs(%)", "Expert Runs (%)",
                 "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)","Predicted Rating", "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)", "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)", "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)", "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)", "4 Guest Airbnb ($/Night)", "2 Guest Airbnb ($/Night)"]
    
    columns_dict = dict(zip(rename_list, rename_to))
    final_recs = final_recs.rename(columns=columns_dict).set_index('Ski Resort')
    return final_recs.head(n_recs).T

def img_text(input_image_path, name):
    image = Image.open(input_image_path)
    draw = ImageDraw.Draw(image)
    font_size = 140  # Set the desired font size
    font_path = "fonts/30270430119.ttf"
    
    # Wrap the text onto multiple lines based on the specified width
    wrapped_text = textwrap.wrap(name, width=10)

    font = ImageFont.truetype(font_path, size=font_size)
    text_color = (255, 0, 189)  # Set the font color as RGB tuple (pink)

    x = 120  # X-coordinate for the text position
    y = 100  # Y-coordinate for the text position

    # Draw each line of wrapped text onto the image
    for line in wrapped_text:
        draw.text((x, y), line, font=font, fill=text_color)
        x = 120
        y = 220

    return image
                 

#st.title("Avant Ski")
#header_placeholder = st.empty()

header_image_path = './images/avant_ski_logo.png'
header_image = Image.open(header_image_path)
st.image(header_image, width=150)

#st.subheader("Ski Resort Recommender")

# user inputs
user = st.text_input('Name')
n_recs = st.number_input('How many resort recommendations do you want?', min_value=1, max_value=10, step=1)
mountain_name = st.selectbox("Choose a resort to find similar recommendations.", resort_names)
travel_date = st.selectbox('What month would you like to travel?', month_list)
mtn_pass = st.radio('Are you using a multi-resort pass?', ('Yes', 'No'))
radio_choices = []
if mtn_pass == 'Yes':
    radio_choices = st.multiselect('Select pass types', pass_list)

# recommendation button
if st.button("Get Recommendations"):
    
    #adding empty header to remove the image
    #header_placeholder.empty()
    
    if user not in user_df.index:
        st.sidebar.error("Please enter a valid name or username.", icon="🚨")
    else:
        # calling model
        recommendations = hybrid_model_content(user, n_recs, mountain_name, travel_date, mtn_pass, radio_choices)

    # Display the final recommendations
    #st.subheader("Ski Resort Recommendations")
    
    #displaying map of ski resorts
    rec_list = recommendations.columns.to_list()
    rec_map_df = content_matrix[content_matrix.index.isin(rec_list)]
    rec_map_df = rec_map_df.reset_index()
    
#     image = Image.open('images/icons/cable-car.png')
    
#     lift_num = rec_map_df['total_lifts'][0]
#     st.image(image, caption=lift_num, width=60)

    rec_map_df.rename(columns={"ski_resort":"Ski Resort"}, inplace=True)
    
    fig = px.scatter_mapbox(rec_map_df, lat='latitude', lon='longitude',
                            hover_name="Ski Resort", hover_data=["summit", "base",
                                                                 "drop"],
                            color='Ski Resort', zoom=2.25)
    
#     loop_list = range(n_recs)
    
#     for x in loop_list:
    
#         fig.add_trace(px.scatter_mapbox(rec_map_df, lat='lat', lon='long',
#                                         color_discrete_sequence=["white"]).data[x])

#         fig.add_trace(px.scatter_mapbox(rec_map_df, lat='lat_2', lon='long_2',
#                                         color_discrete_sequence=["white"]).data[x])

    # Update the map layout
    fig.update_layout(mapbox_style='open-street-map')
    fig.update_layout(margin={'r': 0, 't': 0, 'l': 0, 'b': 0})

    # Display the map
    #st.plotly_chart(fig, use_container_width=True)
    
    
    #making containers for recommendations
    container = st.container()
    
    #setting max container columns to three
    max_columns = 3
    
    #breaking out rows based on column width
    n_rows = (n_recs + max_columns - 1) // max_columns
    
    #adjusting the number of columns/rows based on the length of recommendations
    for row in range(n_rows):
        columns = st.columns(max_columns)
        for col in range(max_columns):
            container = columns[col]
            i = row * max_columns + col
            
            # adding image with resort name to containers. image function is defined above
            if i < n_recs:
                with container:
                    rec = recommendations.iloc[:, i].copy()
                    image_path = f'./images/icons/rec_{i+1}.png'
                    name =  f'{rec.name}'
                    image = img_text(image_path, name)
                    st.image(image, use_column_width='always')
                    rec_df = pd.DataFrame(rec).copy()
                                       
                    rating_df = pd.DataFrame(rec_df.loc["Predicted Rating"])
                    rating = float(rating_df['Predicted Rating'].iloc[0])
                    
                    if 1 <= rating < 2:
                        rating_image_path = './images/icons/one_star.png'
                    elif 2 <= rating < 3:
                        rating_image_path = './images/icons/two_stars.png'
                    elif 3 <= rating < 4:
                        rating_image_path = './images/icons/three_stars.png'
                    elif 4 <= rating < 5:
                        rating_image_path = './images/icons/four_stars.png'
                    else:
                        rating_image_path = '../images/icons/five_stars.png'
                     
                    rating_image = Image.open(rating_image_path)
                    st.image(rating_image, width=100, use_column_width='always')
                    
                    rec_df = rec_df.loc[~(rec_df.index == "Predicted Rating")]

                    html_table = rec_df.to_html(header=False)
                    modified_html_table = html_table.replace('<table', '<table style="border-collapse: collapse;"')
                    st.markdown(modified_html_table, unsafe_allow_html=True)
                    st.markdown('#')
   
    st.plotly_chart(fig, use_container_width=True)

                    
        
        