from datetime import datetime, timedelta

date_str_1 = '04-06-2021 09:29:10'
date_str_2 = '04-06-2021 09:20:37'

date_obj_1 = datetime.strptime(date_str_1, '%d-%m-%Y %H:%M:%S')
date_obj_2 = datetime.strptime(date_str_2, '%d-%m-%Y %H:%M:%S')
print(type(date_obj_1))
print(type(date_obj_2))
newTime = date_obj_2 - date_obj_1
print("NEW_TIME : ", (newTime))
print("NEW_TIME : ", type(newTime))

if(newTime > timedelta(0)):
    print(date_obj_2)
else:
    print(date_obj_1)