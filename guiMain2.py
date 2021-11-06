from kivy.app import App
from kivy.lang import Builder
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager,Screen
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.core.camera import Camera as CoreCamera
from kivy.properties import NumericProperty, ListProperty, BooleanProperty, StringProperty, ObjectProperty
import cv2, base64, requests, os
import os.path
import face_recognition
from kivy.uix.boxlayout import BoxLayout
import time, datetime
from threading import Timer
import compareController as cc
from cvzone.FaceDetectionModule import FaceDetector

detector = FaceDetector()

compareControl = cc.compareController()

import numpy as np
import readRFID as rf
from functools import partial
import RPi.GPIO as GPIO
import MFRC522
#from mfrc522 import MFRC522
import signal, ast
import config as cf
import ast
import mysqlController as msc

accessCon = cf.configuration()
mysqlControl = msc.mysqlController(accessCon)
MIFAREReader = MFRC522.MFRC522()

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    continue_reading = False
    GPIO.cleanup()

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)

readRFID = rf.readRFID()
font = cv2.FONT_HERSHEY_SIMPLEX



# WINDOW CLASSES
class StartWindow(Screen):
    nik = StringProperty('')
    def __init__(self, **kwargs):
        super(StartWindow, self).__init__(**kwargs)
        self.clock1 = None
        
    def on_enter(self):
        self.clock1 = Clock.schedule_interval(self.checkRFIDExistNik,1/30)
    
    def checkRFIDExistNik(self,dt):
        try:
            stats = readRFID.checkIfRFIDTab()
            if(stats):
                # Select the scanned tag
                MIFAREReader.MFRC522_SelectTag(stats[1])
             
                # Authenticate
                status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, 6, stats[2], stats[1])

                # Check if authenticated
                if status == MIFAREReader.MI_OK:
                    datas = MIFAREReader.MFRC522_Read(6)
                    MIFAREReader.MFRC522_StopCrypto1()
                    self.nik = readRFID.deciphereData(datas[1])
                    print(self.nik)
                else:
                    print("Authentication error")
                self.clock1.cancel()
                GPIO.cleanup()
                if(self.nik == 'admin' or self.nik == 'developer'):
                    sm.current = 'endS'
                else:
                    self.checkAccess()
        except Exception as e:
            print(e)
            pass
            
            
    def checkAccess(self):
        print("enter check access")
        query = ""
        staf = False
        if("gst" in self.nik):
            query = f"""
                    SELECT t1.timelimit,t2.log_time,t1.nama
                    from access t1
                    JOIN access_log t2
                    ON t1.gst = t2.gst
                    WHERE t1.gst = "{self.nik}"
                    ORDER BY t2.log_time asc LIMIT 1
                    """
            staf = False
        else:
            query = f"select schedule_in,schedule_out,nama,username from access where nik = {self.nik}"
            staf =True
        
        res = mysqlControl.selectQuery(query)
        print(res)
        if(type(res) != tuple):
            return {
                "return_status":"failed",
                "return_message":res
            }
        else:
            if(staf):
                if(len(res) > 0):
                    schedule_in = str(res[0][0])
                    schedule_in_split = schedule_in.split(":")
                    if(len(schedule_in_split[0]) == 1):
                        schedule_in = "0"+schedule_in
                    schedule_out = str(res[0][1])
                    
                    now = datetime.datetime.now()
                    now = now.strftime("%H:%M:%S")
                    print(schedule_in,now,schedule_out)
                    if schedule_in < now < schedule_out:
                        self.manager.ids.RecogWindow.nama = res[0][2]
                        self.manager.ids.RecogWindow.username = res[0][3]
                        sm.current = "recog"
                    else:
                        self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, schedule anda tidak terpenuhi[/color]'
                        logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_gagal','{self.nik}')"
                        
                        logRes = mysqlControl.CUDQuery(logQuery)
                        print(logRes)
                        sm.current = "endF"
                else:
                    logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_gagal','{self.nik}')"
                    
                    logRes = mysqlControl.CUDQuery(logQuery)
                    print(logRes)
                    self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, schedule anda tidak ditemukan pada database[/color]'
                    sm.current = "endF"
            else:
                if(len(res) == 0):
                    self.manager.ids.EndWindowSuccess.msg.text = '[color=000000]Selamat Datang, [/color]'
                    logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_sukses','{self.nik}')"
                    
                    logRes = mysqlControl.CUDQuery(logQuery)
                    print(logRes)
                    sm.current = "endS"
                else:
                    startTime = res[0][1]
                    timeLimit = res[0][0]
                    now = datetime.datetime.now()
                    now = now.strftime("%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.strptime(now,'%Y-%m-%d %H:%M:%S')
                    if(startTime < now < (now+datetime.timedelta(minutes=timeLimit))):
                        self.manager.ids.EndWindowSuccess.msg.text = f'[color=000000]Selamat Datang, {res[0][2]}[/color]'
                        logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_sukses','{self.nik}')"
                        logRes = mysqlControl.CUDQuery(logQuery)
                        print(logRes)
                        sm.current = "endS"
                        
                

class RecogWindow(Screen,Image):
    nikk = StringProperty('')
    nama = StringProperty('')
    username = StringProperty('')
    def __init__(self, **kwargs):
        super(RecogWindow, self).__init__(**kwargs)
        self.capture = None
        # self.capture.set(3,480)
        # self.capture.set(3,640)
        self.fps = 30
        self.countDown =  5
        self.state = False
        self.recogName = ""
        self.clock1 = None
        self.clock2 = None
        self.nikk = "None"
        print("init recog window")
        
    def on_pre_enter(self):
        self.nikk = self.manager.ids.StartWindow.nik
        self.capture = cv2.VideoCapture(0)
        self.fps = 30
        self.countDown =  5
        self.state = False
        self.recogName = ""
        self.clock1 = None
        self.clock2 = None
        self.closeLimit = 0
        

    def on_enter(self):
        print(f"nik/guessid {self.nikk}")
        self.clock1 = Clock.schedule_interval(self.update, 1.0 / self.fps)
        self.clock2 = Clock.schedule_interval(self.countDownFunc,1)
    
    def on_leave(self):
        self.capture.release()
        self.countDown =  5
        self.closeLimit = 0
        self.clock1.cancel()
        self.clock2.cancel()
    
    def countDownFunc(self,dt):
        if(self.countDown != 0):
            self.countDown -= 1
        else:
            pass
            

    def update(self,dt):
        ret, frame = self.capture.read()
        
        if ret:
            imgS = cv2.resize(frame,(0,0),None,0.25,0.25)
            imgS = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            h,w,c = frame.shape
            startP = (int(w/2-w/4),int(h/2-h/4))
            endP = (int(w/2+w/4),int(h/2+h/4))
            self.draw_border(frame,startP,endP,(17, 233, 24),7, 15, 10)
            img, bboxs = detector.findFaces(frame)
            if bboxs:
                frame = cv2.putText(frame,f"count {self.countDown}", (int(h/2),h-(h-50)), font, 1, (17, 233, 24), 3, cv2.LINE_AA)
                if(self.countDown == 0 and self.state == False):
                    self.recogName = self.faceRecognition(imgS)
                    self.state = True
                if(self.recogName != ""):
                    print(self.recogName,self.nikk)
                    if(self.recogName == self.nikk or self.nikk in self.recogName or self.recogName == self.nama):
                        logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_sukses','{self.nikk}')"
                        
                        logRes = mysqlControl.CUDQuery(logQuery)
                        print(logRes)
                        self.manager.ids.EndWindowSuccess.msg.text = f"[color=2A2A2A]Selamat Datang,{self.nama}[/color]"
                        sm.current = "endS"
                    else:
                        logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_gagal','{self.nikk}')"
                        logRes = mysqlControl.CUDQuery(logQuery)
                        print(logRes)
                        self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, Wajah anda gagal diverifikasi[/color]'
                        sm.current = "endF"
                elif(self.recogName == "" and self.countDown == 0):
                    self.state = False
                    self.closeLimit += 1 
                    self.countDown = 5
                    frame = cv2.putText(frame,f"fail get face, retry in {self.countDown}", (int(h/3),h-(h-50)), font, 1, (17, 233, 24), 3, cv2.LINE_AA)
                if(self.closeLimit == 3):
                    logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_gagal','{self.nikk}')"
                    logRes = mysqlControl.CUDQuery(logQuery)
                    print(logRes)
                    self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, Wajah anda gagal diverifikasi[/color]'
                    sm.current = "endF"
                    
            # convert it to texture
            buf1 = cv2.flip(frame, 0)
            buf = buf1.tobytes()
            image_texture = Texture.create(
                size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            # display image from the texture
            self.texture = image_texture
    
    def draw_border(self,img, pt1, pt2, color, thickness, r, d):
        x1,y1 = pt1
        x2,y2 = pt2
        # Top left
        cv2.line(img, (x1 + r, y1), (x1 + r + d, y1), color, thickness)
        cv2.line(img, (x1, y1 + r), (x1, y1 + r + d), color, thickness)
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
        # Top right
        cv2.line(img, (x2 - r, y1), (x2 - r - d, y1), color, thickness)
        cv2.line(img, (x2, y1 + r), (x2, y1 + r + d), color, thickness)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
        # Bottom left
        cv2.line(img, (x1 + r, y2), (x1 + r + d, y2), color, thickness)
        cv2.line(img, (x1, y2 - r), (x1, y2 - r - d), color, thickness)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
        # Bottom right
        cv2.line(img, (x2 - r, y2), (x2 - r - d, y2), color, thickness)
        cv2.line(img, (x2, y2 - r), (x2, y2 - r - d), color, thickness)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)
    
    def faceRecognition(self,imgS):
        cv2.imwrite("frame.jpg", imgS)
        res = "frame.jpg"
        name = ""
        
        image_name = self.nikk + "_" + self.username
        print(f"try recog {image_name}")
        dirImageNameExist = os.path.isdir(f"images/{image_name}")
        if(dirImageNameExist == False):
            print("not exist dir",dirImageNameExist,f"images/{image_name}")
            return "unknown"
        else:
            picture_to_predic = face_recognition.load_image_file(f"images/{image_name}/{image_name}.jpg")
            
            my_face_encoding = face_recognition.face_encodings(picture_to_predic)[0]
            for i in range(4):
                unknown_picture = face_recognition.load_image_file(res)
                unknown_face_encoding = face_recognition.face_encodings(unknown_picture)
                if(len(unknown_face_encoding) == 0):
                    self.rot(res,90)
                else:
                    break
            if(len(unknown_face_encoding) != 0):
                unknown_face_encoding = unknown_face_encoding[0]
                results = face_recognition.compare_faces([my_face_encoding], unknown_face_encoding,tolerance=0.4)
                # print(unknown_face_encoding)
                if results[0] == True:
                    masterImg = f"images\\{image_name}\\{image_name}.jpg"
                    return self.nama
                else:
                    return "unknown"
            else:
                return ""
        
    def most_frequent(self,List): 
        return max(set(List), key = List.count)
    

    
class EndWindowFail(Screen):
    msgId = ObjectProperty(None)
    def on_enter(self):
        Clock.schedule_once(self.backToMain,3)
    
    def backToMain(self,dt):
        sm.current = "start"

class EndWindowSuccess(Screen):
    msg = ObjectProperty(None)
    def on_enter(self):
        Clock.schedule_once(self.backToMain,3)
    
    def backToMain(self,dt):
        sm.current = "start"

class WindowManager(ScreenManager):
    pass




kv = Builder.load_file("ui.kv")
sm = WindowManager()

screens = [StartWindow(name="start"),RecogWindow(name="recog"),EndWindowFail(name="endF"),EndWindowSuccess(name="endS")]
for screen in screens:
    sm.add_widget(screen)

sm.current = "start"

class smartAccessApp(App):
    def build(self):
        return sm
    

if __name__ == "__main__":
    smartAccessApp().run()
