import csv
import datetime
import math
from multiprocessing.sharedctypes import Value
from csvtools import csv_open
from utils import secToTime, printProgressBar
INPUT_SAMPLING_TIME = 1800
SECONDS_IN_DAY = 86400
SAMPLING_TIME = 3600

def getWeekDayFromDate(dt: str, sep="/"):
    dtsep = dt.split(sep)
    day = int(dtsep[0])
    month = int(dtsep[1])
    year = int(dtsep[2])
    date = datetime.datetime(year=year, month=month, day=day)
    return date.weekday()

def getArrayFromString(input: str, typ=int):
    rtlist = []
    s1 = input.split("[")
    s2 = s1[1].split("]")
    lst = s2[0].split(",")
    for el in lst:
        rtlist.append(typ(el))
    return rtlist

def nexT(hour,shift):
    t = hour.split(":")
    s1 = int(t[0])*3600 + int(t[1])*60
    s = s1 + shift*SAMPLING_TIME
    return secToTime(s,clockFormat=True)


def main(users_number):
    trajectories = csv_open("DATASET/trajectories.csv",sep=";")
    user_hyper_matrix = [{},{},{},{},{},{},{}]
    for dic in user_hyper_matrix:
        i = 0
        while i<SECONDS_IN_DAY:
            hid = secToTime(i,clockFormat=True)
            dic[hid] = []
            for j in range(users_number):
                dic[hid].append([])
            i += SAMPLING_TIME
    cnt = 0
    for line in trajectories:
        index = getWeekDayFromDate(line["date"])
        arr_times_list = getArrayFromString(line["arrival_times"])
        poi_list = getArrayFromString(line["trajectory"])
        perm_list = getArrayFromString(line["permanence_times"])
        user = int(line["uid"])
        visited_places = len(arr_times_list)
        for i in range(visited_places):
            time = (arr_times_list[i] * INPUT_SAMPLING_TIME)
            carry = time % SAMPLING_TIME
            t_elem = time - carry
            hid = secToTime(t_elem,clockFormat=True)
            hid.split(":")
            # hour_numeric_index = hid[0]
            perm_minutes = perm_list[i]
            perm_secs = perm_minutes * 60
            h_carry = perm_secs % SAMPLING_TIME
            elem = [None,None]
            h_shift = math.floor(perm_secs / SAMPLING_TIME)
            if h_shift > 0 :
                for j in range(h_shift):
                    if j != h_shift - 1: 
                        elem = [poi_list[i], 60]
                    else: 
                        elem = [poi_list[i], math.floor(h_carry/60)]
                    user_hyper_matrix[index][nexT(hid,j)][user].append(elem)
            else:
                elem = [poi_list[i],perm_list[i]]
                user_hyper_matrix[index][hid][user].append(elem)
        cnt += 1
        printProgressBar(cnt,len(trajectories),length=10,prefix=" loading")

    return user_hyper_matrix

# (DA IMPLEMENTARE)
# Al momento vengono pesati gli spostamenti tutti allo stesso modo
# Si potrebbe (deve) dar più peso agli spostamenti e le abitudini più recenti

def predictZone(uhm,day_of_week,desired_time,desired_user):
    park_zone_list = uhm[day_of_week][desired_time][desired_user]
    print(park_zone_list)
    dct = {}
    for el in park_zone_list:
        if el[0] not in dct:
            dct[el[0]] = [el[1]]
        else:
            dct[el[0]].append(el[1])
    weightList = []
    lenList = []
    for key in dct:
        weightList.append(sum(dct[key]))
        lenList.append(len(dct[key]))
    try:
        maxEl = max(weightList)
        id = weightList.index(maxEl)
        time = maxEl / lenList[id]
        return time, list(dct)[id]
    except ValueError:
        print("User",desired_user,"have no preferences yet for time:",desired_time)
        return None, None


if __name__ == "__main__":
    users_number = 151

    desired_user = 1
    desired_time = "14:00"
    day_of_week = 2

    uhm = main(users_number)
    try:
        time, zone = predictZone(uhm,day_of_week,desired_time,desired_user)
        time = secToTime(time*60,clockFormat=True,hs=True)
        print("UserID:",desired_user,"day of week:",day_of_week,"desired time:",desired_time," WANTS TO PARK HERE ->",zone,"FOR ABOUT:",time)
    except TypeError:
        pass