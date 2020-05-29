def extract(username, file_dir):
	"""Extracts data from chess.com site. Return a dataframe."""

	import os
	import numpy as np
	import pandas as pd
	import io
	from datetime import datetime
	import time

	# API Library
	import requests

	# Chess Package
	import chess.pgn

	def chess_api(api):
	    api_success = 0 

	    try:
	        response = requests.get(api)
	    except:
	        print('API Error - Could not make request (Possible API Configuration Issue)')
	        print(f'API: {api}')

	    else:
	        if response.status_code != 200: 
	            print('API Error - Request made but error code returned')
	            print(f'Response Code: {response.status_code} ({response.reason})')
	        else:
	            api_success = 1

	        #print(f'Response Time: {response.elapsed.total_seconds()} sec\
	        #({response.elapsed.microseconds}ms)')
	    
	    if response.status_code == 200:
	    # Store Data in Dictionary
	        try:
	            user_dict = response.json()
	        except:
	            print('Error converting data from JSON response to python dictionary')

	        finally:
	            response.close()
	    
	    return user_dict
    

	# Function to extract user metadata
	def user_info(username):
	    user_dict = chess_api(f"https://api.chess.com/pub/player/{username}")

	    # Clean up dictionary
	    try:
	        user_dict['country'] = user_dict['country'][(user_dict['country'].rfind('/')+1):] # Extract Country from end of URL
	        user_dict['user_active_days'] = (datetime.utcfromtimestamp(user_dict['last_online']) - datetime.utcfromtimestamp(user_dict['joined'])).days
	        user_dict['joined'] = datetime.utcfromtimestamp(user_dict['joined']).strftime('%Y-%m-%d')
	        user_dict['last_online'] = datetime.utcfromtimestamp(user_dict['last_online']).strftime('%Y-%m-%d')

	    except:
	        print('Error cleaning up user meta data dictionary')
	        
	    return user_dict 

	# Function to extract user stats
	def user_stats(username):
	    user_stats_dict = chess_api(f"https://api.chess.com/pub/player/{username}/stats")
	    return user_stats_dict
    

	def extract_game_data(game):
	    
	    # Game Type
	    game_type = f"{game['rules']}_{game['time_class']}"
	    
	    # Identify if player was black or white
	    white_peices = 0
	    if game['white']['username'] == username:
	        player_dict = game['white']
	        opp_dict = game['black']
	        white_peices = 1
	    elif game['black']['username'] == username:
	        player_dict = game['black']
	        opp_dict = game['white']
	        white_peices = 0
	    else:
	        raise Exception(f"Error - Cannot identify user as black/white in game (Game URL: {game['url']})")    
	    
    	# Get opponent info
	    try:
	        opp_info = user_info(opp_dict['username'])
	    except:
	        opp_info = {'country': None,
	                    'joined': None,
	                    'status': None}
	        
	    # Get opponent stats
	    try:
	        opp_stats = user_stats(opp_dict['username'])
	        ## Get Stats for this game type
	        opp_stats = opp_stats[game_type]
	    except:
	        opp_stats = {'record': {'win': None, 'loss': None, 'draw': None} }
	    
	    try:
	        # Read the PGN of the game details
	        pgn = io.StringIO(game['pgn'])
	        game_details = chess.pgn.read_game(pgn)
	    except:
	        print('Error reading png file using the chess chess.pgn.read_game function')
	            
	    
	    player_first_moves, opp_first_moves, game_len = first_x_moves(game_details, white_peices, x=5)

	    feature_df = {
	        'game_type': game_type,
	        'game_rules': game['rules'],
	        'time_class': game['time_class'],
	        'time_control_sec': int(game['time_control']),
	        'time_control_min': int(game['time_control'])/60,
	        'game_url': game['url'],
	        'game_id': game['url'][(game['url'].rfind('/')+1):],
	        'game_site': game_details.headers['Site'],
	        'game_date': game_details.headers['Date'],
	        'game_time': game_details.headers['StartTime'],
	        'player_rating_post': player_dict['rating'],
	        'player_whites': white_peices,
	        'opponent_name': opp_dict['username'],
	        'opponent_rating_post': opp_dict['rating'],
	        'opponent_result': opp_dict['result'],
	        'opponent_country': opp_info['country'],
	        'opponent_joined': opp_info['joined'],
	        'opponent_status': opp_info['status'],
	        'opponent_win': opp_stats['record']['win'],
	        'opponent_loss': opp_stats['record']['loss'],
	        'opponent_draw': opp_stats['record']['draw'],
	        'player_eco': game_details.headers['ECO'],
	        'player_move_1': player_first_moves[0],
	        'player_move_2': player_first_moves[1],
	        'player_move_3': player_first_moves[2],
	        'player_move_4': player_first_moves[3],
	        'player_move_5': player_first_moves[4],
	        'opp_move_1': opp_first_moves[0],
	        'opp_move_2': opp_first_moves[1],
	        'opp_move_3': opp_first_moves[2],
	        'opp_move_4': opp_first_moves[3],
	        'opp_move_5': opp_first_moves[4],
	        'game_length': game_len,
	        'result': player_dict['result']
	        }
	    return feature_df


	## Function to extract list of first x moves
	def first_x_moves(game_details, white_peices, x=5):
	    white_moves = []
	    black_moves = []

	    player_first_moves = [None]*x
	    opp_first_moves = [None]*x
	    
	    try:
	        game_moves = list(game_details.mainline_moves())
	        game_moves = [i.uci() for i in game_moves]

	        for i in range(len(game_moves)):
	            if i % 2 == 0:
	                white_moves.append(game_moves[i])
	            else:
	                black_moves.append(game_moves[i])
	    except:
	        print('Error Extracting game moves from png file inside the first_x_moves function')

	    if white_peices == 0:
	        player_first_moves = (white_moves + [None]*(x - len(white_moves)))[:x]
	        opp_first_moves = (black_moves + [None]*(x - len(black_moves)))[:x]
	    else:
	        opp_first_moves = (white_moves + [None]*(x - len(white_moves)))[:x]
	        player_first_moves = (black_moves + [None]*(x - len(black_moves)))[:x]
	    
	    game_len = len(white_moves)
	    
	    return player_first_moves, opp_first_moves, game_len


    # Initilize Dataframe
	game_df = pd.DataFrame(columns =['game_type', 'game_rules', 'time_class', 
	                                 'time_control_sec', 
	                                 'time_control_min', 'game_url', 'game_id', 
	                                 'game_site', 'game_date', 'game_time', 
	                                 'player_rating_post', 'player_whites', 
	                                 'opponent_name', 'opponent_rating_post', 
	                                 'opponent_result', 'opponent_country', 'opponent_joined',
	                                 'opponent_status', 'opponent_win', 'opponent_loss',
	                                 'opponent_draw', 'player_eco', 
	                                 'player_move_1','player_move_2', 'player_move_3',
	                                 'player_move_4', 'player_move_5',
	                                 'opp_move_1', 'opp_move_2', 'opp_move_3',
	                                 'opp_move_4', 'opp_move_5', 'game_length',
	                                 'result'])

	user_game_months = chess_api(f"https://api.chess.com/pub/player/{username}/games/archives")

	# Create dictionary to output as 1 row to dataframe
	feature_df = {}

	for mth in user_game_months['archives']:
	    all_game_data = chess_api(mth)
	    for game in all_game_data['games']:
	        time.sleep(1)
	        game_dict = extract_game_data(game)
	        temp_df = pd.DataFrame(columns=game_dict.keys())
	        temp_df = temp_df.append(game_dict, ignore_index=True)
	        
	        # Append to final dataframe
	        game_df = game_df.append(temp_df)

	return  game_df

