import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import pandas as pd
import os 
import pyshorteners as ps

def ask_user_search_again():
    search_again = input('Would you like to search again? [y/n]\n')
    while search_again != 'y' and search_again != 'n':
        print('ERROR: Enter only \'y\' or \'n\'')
        search_again = input('Would you like to search again? [y/n]\n')
    if search_again == 'y':
        print('\n')
        main()
    elif search_again == 'n':
        print('\nThanks for using DogFinder; you are now exiting the program.')
        exit()
    
def ask_user_to_save(df):
    df = df.reset_index()
    choice = input('\nDo you want to save any of these results? [y/n]\n')
    while choice != 'y' and choice != 'n':
        print('ERROR: Enter only \'y\' or \'n\'')
        choice = input('\nDo you want to save any of these results? [y/n]\n')
    if choice == 'y':
        number_of_dogs = input('How many?\n')
        dog_ids = []
        for i in range(int(number_of_dogs)):
            dog_id = input('For dog #' + str(i+1) + ', enter its id: ')
            dog_ids.append(int(dog_id))
        saved_results_df = df[df['id'].isin(dog_ids)]
        saved_results_df = saved_results_df.set_index('id')
        output_path='saved_results.csv'
        saved_results_df.to_csv(output_path, mode='a', header=not os.path.exists(output_path))

        print('\nSAVED RESULTS BELOW')
        dataframe = pd.read_csv(output_path)
        dataframe = dataframe.set_index('id')
        print(dataframe)
        print('\n')
        
        ask_user_search_again()
    elif choice == 'n':
        ask_user_search_again()

def make_url(user_location,distance,breed,size,gender,age):
    URL = 'https://api.petfinder.com/v2/animals?type=Dog&limit=50'
    if user_location:
        location_query_param = '&location=' + user_location
        URL += location_query_param
    if distance: 
        distance_query_param = '&distance=' + distance
        URL += distance_query_param
    if breed:
        breed_query_param = '&breed=' + breed
        URL +=  breed_query_param
    if size:
        size_query_param = '&size=' + size
        URL += size_query_param
    if gender:
        gender_query_param = '&gender=' + gender
        URL += gender_query_param
    if age:
        age_query_param = '&age=' + age
        URL += age_query_param
    return URL

def parse_and_print_results(json_data, dogs):
    df = pd.DataFrame(index=range(len(dogs)),columns=['id', 'Name', 'Primary_Breed', 'Gender', 'Age', 'Size', 'URL_to_Profile'])
    df['id'] = [dog['id'] for dog in dogs]
    df['Name'] = [dog['name'] for dog in dogs]
    df['Primary_Breed'] = [dog['breeds']['primary'] for dog in dogs]
    df['Age'] = [dog['age'] for dog in dogs]
    df['Size'] = [dog['size'] for dog in dogs]
    df['Gender'] = [dog['gender'] for dog in dogs]
    df['URL_to_Profile'] = [ps.Shortener().tinyurl.short(dog['url']) for dog in dogs]
    df = df.set_index('id')
    total_count = json_data['pagination']['total_count']
    print('\nSHOWING ' + str(len(dogs)) + ' OUT OF ' + str(total_count) + ' RESULTS')
    print(df)
    ask_user_to_save(df)

def main():
    client = BackendApplicationClient(client_id='KvzDELJ9HevuTpoOgBIva4rMUamUcW9an0cWkT4iMzyNQ1pNgj')
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(token_url='https://api.petfinder.com/v2/oauth2/token', client_id='KvzDELJ9HevuTpoOgBIva4rMUamUcW9an0cWkT4iMzyNQ1pNgj',client_secret='rO40JVot0cRxi4K8K8uV8MuaNNhl0T750Gngm45p')
    access_token = token['access_token']
    
    print('Welcome to DogFinder!\n')
    user_location = input('Enter your zip code (optional): ')
    distance = input('Enter distance in miles (optional): ')
    breed = input('Enter desired breed, if any: ')
    size = input('Enter desired size, if any:\n'
                + '[1] small\n[2] medium\n[3] large\n[4] xlarge\n')
    if size:
        if size == '1':
            size = 'small'
        elif size == '2':
            size = 'medium'
        elif size == '3':
            size = 'large'
        elif size == '4':
            size = 'xlarge'
    gender = input('Enter desired gender, if any:\n[1] male\n[2] female\n')
    if gender:
        if gender == '1':
            gender = 'male'
        elif gender == '2':
            gender = 'female'
    age = input('Enter the age range you would like to search for, if any:\n'
                + '[1] baby\n[2] young\n[3] adult\n[4] senior\n')
    if age:
        if age == '1':
            age = 'baby'
        elif age == '2':
            age = 'young'
        elif age == '3':
            age = 'adult'
        elif age == '4':
            age = 'senior'
    URL = make_url(user_location,distance,breed,size,gender,age)

    r = requests.get(URL, headers={ 'Authorization': 'Bearer ' + access_token})
    json_data = r.json()
    if json_data['animals'] == []:
        print('NO RESULTS FOUND')
        ask_user_search_again()
    else:
        dogs = json_data['animals']
        parse_and_print_results(json_data, dogs)


if __name__ == '__main__':
    main()