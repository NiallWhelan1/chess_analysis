def prepare(game_data, game_type = 'chess_blitz', game_time_sec = 600):

	import os
	import numpy as np
	import pandas as pd

	from datetime import datetime

	#### Initial Clean-up ####

	game_data = game_data[(game_data['game_type'] == game_type) & (game_data['time_control_sec'] == game_time_sec)]

	## Drop rows if missing data from API
	num_rows_miss_info = len(game_data) - len(game_data.dropna(axis = 0))
	if num_rows_miss_info > 0:
	    print(f'Missing Data (Usually API Issue) - Dropped {num_rows_miss_info} Rows')
	    game_data = game_data.dropna(axis = 0)

	game_data = game_data.reset_index()

	## Remove unused columns
	game_data = game_data.drop(['game_type','game_rules','time_class',
	                            'time_control_sec','time_control_min','game_url',
	                            'game_site','index'], 
	                           axis = 1)

	## Clean up dates & times

	#### Game Date
	game_data['game_date_time'] = game_data['game_date'].str.cat(game_data['game_time'], sep = ' - ')

	game_data['game_date_time'] = game_data['game_date_time'].apply(datetime.strptime, 
	                                                          args=('%Y.%m.%d - %H:%M:%S',))

	game_data['game_date'] = game_data['game_date_time'].dt.date
	game_data['game_time'] = game_data['game_date_time'].dt.time

	#### Opponent Joined Date
	game_data['opponent_joined'] = game_data['opponent_joined'].apply(datetime.strptime, 
	                                                          args=('%Y-%m-%d',)).dt.date

	## Ensure sorting is in place
	game_data = game_data.sort_values(by = 'game_date_time', ascending=True)

	#### Target Variable Clean Up ####
	## Target Variables (Binary and multi-call [includes draw])
	result_list_bin = []
	result_list_multi = []
	for i in game_data['result']:
	    if i == 'win':
	        result_list_bin.append(1)
	        result_list_multi.append(1)
	    elif i in ['checkmated','resigned','timeout']:
	        result_list_bin.append(0)
	        result_list_multi.append(0)
	    else:
	        result_list_bin.append(0)
	        result_list_multi.append(2)

	game_data['result_binary'] = result_list_bin
	game_data['result_multi_class'] = result_list_multi

	#### Feature generation ####

	## Hour Feature
	game_data['game_time_hour'] = game_data['game_date_time'].dt.hour

	## Day of Week
	game_data['game_day_of_week'] = game_data['game_date_time'].dt.dayofweek

	## opponent time since joined
	game_data['opponant_tsj'] = (game_data['game_date'] - game_data['opponent_joined']).dt.days

	game_data['opponant_all_games'] = game_data[['opponent_draw',
	                                             'opponent_win',
	                                             'opponent_loss']].sum(axis =1)


	## Get points earned/lost per game
	game_data = game_data.sort_values(by = 'game_date_time')
	game_data['player_point_change'] = game_data['player_rating_post'].diff().fillna(0)
	## Calculate score at start of game
	game_data['player_rating_pre'] = game_data['player_rating_post'] - game_data['player_point_change']

	## Game counts - ever, day, hour
	game_data['cum_games_played'] = list(game_data.index)

	#### Day
	games_today = []
	curr_day = min(game_data['game_date'])
	day_count = 0
	for i in game_data['game_date']:
	    if i == curr_day:
	        day_count += 1
	    else:
	        day_count = 1
	        curr_day = i
	    games_today.append(day_count)

	game_data['cum_games_today'] = games_today

	#### Hour
	games_hour = []
	curr_hour = min(game_data['game_date_time'].dt.floor(freq = 'h'))
	hr_count = 0
	for i in game_data['game_date_time'].dt.floor(freq = 'h'):
	    if i == curr_hour:
	        hr_count += 1
	    else:
	        hr_count = 1
	        curr_hour = i
	    games_hour.append(hr_count)

	game_data['cum_games_hour'] = games_hour


	## Cumulative player wins
	game_data['cum_wins'] = game_data['result_binary'].cumsum()
	game_data['cum_non_wins'] = game_data['cum_games_played'] - game_data['cum_wins']

	return game_data