import sys
from fastapi import FastAPI
from parkUserTracking import makePrediction, getUserCount, getUserHyperMatrix
import csvtools as ct
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, BaseSettings
import re
from utilities import bcolors

class EnVar(BaseSettings):
    ds: ct.CsvDataFrame = None
    uhm: list = None
    def getUserHyperMatrix(self, forceUpdate = False):
        if self.ds is None or forceUpdate:
            self.ds = ct.csv_open("DATASET/trajectories.csv",sep=";")
            user_count = getUserCount(self.ds)
            self.uhm = getUserHyperMatrix(user_count, self.ds)
        return self.uhm

class Req(BaseModel):
    desired_user: int
    desired_time: str
    desired_date: str

app = FastAPI()
enVar = EnVar()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/api/smartep_ia/user_behavoir/predict")
async def create_item(item: Req):
    desired_user = int(item.desired_user)
    desired_time = str(item.desired_time)
    desired_date = str(item.desired_date)
    uhm = enVar.getUserHyperMatrix()
    res = makePrediction(uhm,desired_user,desired_time,desired_date)
    return res

if __name__ == "__main__":
    prt = 5001
    hst = "127.0.0.1"
    p = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    try:
        if sys.argv[1] is None:
            print("Usage: " + sys.argv[0] + " [address] [port]")
            print("Starting server using default address:",hst)
        else:
            temp = str(sys.argv[1])
            if p.match(temp):
                hst = temp
                print("Starting server using address:",hst)
            else:
                print(bcolors.FAIL+"ERROR: You must specify a valid address (like 127.0.0.1)"+bcolors.ENDC)
                print(bcolors.WARNING+"Starting server using default address: "+str(hst)+bcolors.ENDC)
        if sys.argv[2] is None:
            print(bcolors.WARNING+"Starting server using default server port: "+prt+bcolors.ENDC)
        else:
            try:
                prt = int(sys.argv[2])
                print("Starting server using port:",prt)
            except:
                print(bcolors.FAIL+"ERROR: You must specify an integer value for server port."+bcolors.ENDC)
                print(bcolors.WARNING+"Starting server using default server port: "+str(prt)+bcolors.ENDC)
    except IndexError:
        print(bcolors.WARNING+"Usage: " + sys.argv[0] + " [address] [port]"+bcolors.ENDC)
        print("Starting server using default server port:",prt)
    uvicorn.run("server:app", host=hst, port=prt, log_level="info")