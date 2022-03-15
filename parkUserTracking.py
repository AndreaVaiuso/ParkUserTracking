import datetime
import random
import math
from csvtools import getArrayFromString, arrayToString, CsvDataFrame
from utilities import secToTime, timeToSec, printProgressBar

INPUT_SAMPLING_TIME = 1800
SECONDS_IN_DAY = 86400
SAMPLING_TIME = 3600


def getWeekDayFromDate(dt:str, sep:str="/"):
    dtsep = dt.split(sep)
    day = int(dtsep[0])
    month = int(dtsep[1])
    year = int(dtsep[2])
    date = datetime.datetime(year=year, month=month, day=day)
    return date.weekday()

def nexT(hour:str,shift:int):
    t = hour.split(":")
    s1 = int(t[0])*3600 + int(t[1])*60
    s = s1 + shift*SAMPLING_TIME
    return secToTime(s,clockFormat=True)

def initHyperMatrix(total_user_count):
    user_hyper_matrix = [{},{},{},{},{},{},{}]
    for dic in user_hyper_matrix:
        i = 0
        while i<SECONDS_IN_DAY:
            hid = secToTime(i,clockFormat=True)
            dic[hid] = []
            for j in range(total_user_count):
                dic[hid].append([])
            i += SAMPLING_TIME
    return user_hyper_matrix

def getUserHyperMatrix(total_user_count:int,traj:CsvDataFrame):
    trajectories = traj.getDataFrame()
    user_hyper_matrix = initHyperMatrix(total_user_count)
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
            perm_minutes = perm_list[i]
            # Amount of seconds of permanence in that poi
            perm_secs = perm_minutes * 60
            # How many time slots are occupied from that user
            h_shift = math.floor(perm_secs / SAMPLING_TIME)
            # Amount of seconds in the last time slot of occupation for that parking
            h_carry = perm_secs % SAMPLING_TIME
            # Amount of minutes in a sampling time
            maxval = SAMPLING_TIME / 60
            elem = [None,None]
            if h_shift > 0 :
                for j in range(h_shift):
                    if j != h_shift - 1: 
                        elem = [poi_list[i], maxval]
                    else: 
                        elem = [poi_list[i], math.floor(h_carry/maxval)]
                    user_hyper_matrix[index][nexT(hid,j)][user].append(elem)
            else:
                elem = [poi_list[i],perm_list[i]]
                user_hyper_matrix[index][hid][user].append(elem)
        cnt += 1
        printProgressBar(cnt,len(trajectories),length=10,prefix=" loading")
    return user_hyper_matrix

def generateWeights(size,firstElementGain=1):
    weights = []
    for x in range(size):
        val = -math.atan(x)+(math.pi/2)
        if x == 0: val *= firstElementGain
        weights.append(val)
    nfac = 1/sum(weights)
    for i in range(len(weights)):
        weights[i] = weights[i] * nfac
    return weights

def weightedMean(data_array,weights):
    weighted_data = [0] * len(data_array[0])
    for i in range(len(data_array[0])):
        for j in range(len(weights)):
            weighted_data[i]+= data_array[j][i] * weights[j]
    return weighted_data

def normalize(arr, t_min=0, t_max=1):
    norm_arr = []
    diff = t_max - t_min
    diff_arr = max(arr) - min(arr)   
    for i in arr:
        temp = (((i - min(arr))*diff)/diff_arr) + t_min
        norm_arr.append(temp)
    return norm_arr

def perc(arr,vmax=1):
    y = []
    sval = sum(arr)
    if sval == vmax:
        return arr
    for val in arr:
        y.append(((vmax/sval) * val))
    return y

def dictperc(dct,vmax=1):
    val_list = []
    for key in dct:
        val_list.append(dct[key])
    val_list = perc(val_list)
    i = 0
    for key in dct:
        dct[key] = val_list[i]
        i += 1
    return dct

def getInterestedTimeZone(times,desired_time):
    secs = timeToSec(desired_time)
    diff = float("inf")
    i = 0
    for i in range(len(times)):
        n_diff = abs(secs - timeToSec(times[i]))
        if diff < n_diff:
            i -= 1
            break
        diff = n_diff
    return times[i]

def alterate(alt_dct:dict,zone_dct:dict):
    if alt_dct == {}:
        return zone_dct
    alt_dct = dictperc(alt_dct)
    final_zone_dct = zone_dct
    for key in alt_dct:
        try:
            final_zone_dct[key] = (final_zone_dct[key] + alt_dct[key]) / 2
        except KeyError:
            final_zone_dct[key] = alt_dct[key] / 2
    final_zone_dct = dictperc(final_zone_dct)
    return dict(sorted(final_zone_dct.items(), key=lambda item: item[1], reverse=True))

def predictZone(uhm:list,day_of_week:int,desired_time:str,desired_user:int):
    tz = getInterestedTimeZone(list(uhm[day_of_week]),desired_time)
    park_zone_list = uhm[day_of_week][tz][desired_user]    
    if desired_user < 0:
        raise ValueError()
    dct = {}
    if not park_zone_list:
        return {}
    l = len(park_zone_list)
    wlist = generateWeights(l)
    wlist.reverse()
    i = 0
    for el in park_zone_list:
        w = el[1] * wlist[i]
        if el[0] not in dct:
            dct[el[0]] = w
        else:
            dct[el[0]] += w
        i += 1
    plist = []
    for el in dct:
        plist.append(dct[el])
    plist = perc(plist)
    i = 0
    for el in dct:
        dct[el] = plist[i]
        i += 1
    out = dict(sorted(dct.items(), key=lambda item: item[1], reverse=True))
    return out

def selectAndReplace(dataFrame:CsvDataFrame,plist:list):
    trajectories = dataFrame.getDataFrame()
    for j in range(len(trajectories)):
        poi_list = getArrayFromString(trajectories[j]["trajectory"])
        for i in range(len(poi_list)):
            if poi_list[i] not in plist:
                poi_list[i] = plist[random.randint(0,(len(plist)-1))]
        trajectories[j]["trajectory"] = arrayToString(poi_list)
    return CsvDataFrame(trajectories)

def alterUID(dataFrame:CsvDataFrame):
    trajectories = dataFrame.getDataFrame()
    for line in trajectories:
        uid = int(line["uid"])
        line["uid"] = str(uid-1)
    return CsvDataFrame(trajectories)

def selectAndDel(dataFrame:CsvDataFrame,plist:list):
    trajectories = dataFrame.getDataFrame()
    j = 0
    w = len(trajectories)
    while j < w:
        poi_list = getArrayFromString(trajectories[j]["trajectory"])
        at = getArrayFromString(trajectories[j]["arrival_times"])
        pt = getArrayFromString(trajectories[j]["permanence_times"])
        st = getArrayFromString(trajectories[j]["sem_trajectory"])
        i = 0
        r = len(poi_list)
        while i < r:
            if poi_list[i] not in plist:
                del poi_list[i]
                del at[i]
                del pt[i]
                del st[i]
            else:
                i += 1
            r = len(poi_list)
        if not poi_list:
            del trajectories[j]
        else:
            trajectories[j]["trajectory"] = arrayToString(poi_list)
            trajectories[j]["arrival_times"] = arrayToString(at)
            trajectories[j]["permanence_times"] = arrayToString(pt)
            trajectories[j]["sem_trajectory"] = arrayToString(st)
            j += 1
        w = len(trajectories)
    return CsvDataFrame(trajectories)

def getUserCount(csvdf:CsvDataFrame):
    uc = csvdf.getColumn("uid")
    u_set = set(uc)
    return len(u_set)

def makePrediction(uhm,desired_user,desired_time,desired_date):
    try:
        day_of_week = getWeekDayFromDate(desired_date)
        zoneDct = predictZone(uhm,day_of_week,desired_time,desired_user)
    except (ValueError, KeyError, IndexError) as e:
        return {"status":"error","reply-type":"empty","msg":"Request not valid"}
    zoneDct = alterate({},zoneDct)
    if not zoneDct:
        return {"status":"ok","reply-type":"empty"}
    zoneDct["status"] = "ok"
    zoneDct["reply-type"] = "not-empty"
    return zoneDct
