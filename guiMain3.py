from kivy.config import Config
Config.set('graphics', 'width', '1366')
Config.set('graphics', 'height', '768')
#Config.set('graphics', 'maxfps', 1)


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
import time, datetime, requests, base64
from threading import Timer
import subprocess
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

#Window.fullscreen = True

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
		#Config.set('graphics', 'maxfps', 1)
        
	def on_enter(self):
		subprocess.Popen(["python3","relay_on.py"], stdout=subprocess.PIPE, shell=False)
		self.clock1 = Clock.schedule_interval(self.checkRFIDExistNik,1/30)
    
	#def putHigh(self,dt):
		# print("trigger high")
		# relay.gpio_out_high()
    
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
						
						if(self.nik == ""):
							self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, nik anda tidak ditemukan pada rfid[/color]'
							sm.current = 'endF'
					else:
						print("Authentication error")
						getUID = readRFID.readUUID()
						
						if(getUID == False):
							self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, kartu atau UID anda tidak dikenal[/color]'
							sm.current = 'endF'
						else:
							query = f"select * from uid_table where uid = '{getUID}'"
							res = mysqlControl.selectQuery(query)
							if(type(res) != tuple):
								print(res)
								self.manager.ids.EndWindowFail.msgId.text = f'[color=000000]{res}[/color]'
								sm.current = 'endF'
							else:
								if(len(res) > 0):
									print(res[0][0],res[0][1])
									self.nik = res[0][1]
								else:
									self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, nik untuk uid kartu anda tidak ditemukan[/color]'
									self.nik = ""
									sm.current = 'endF'
					self.clock1.cancel()
					GPIO.cleanup()
					if(self.nik == 'admin' or self.nik == 'developer'):
						self.manager.ids.EndWindowSuccess.msg.text = '[color=000000]Selamat Datang, Developer-sama[/color]'
						sm.current = 'endS'
					elif(self.nik == ""):
						sm.current = 'endF'
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
						ON t1.gst = t2.created_by
						WHERE t1.gst = "{self.nik}" AND DATE(log_time) = DATE(NOW())
						ORDER BY t2.log_time asc LIMIT 1
						"""
				print(query)
				staf = False
		else:
				query = f"select schedule_in,schedule_out,nama,username from access where nik = {self.nik}"
				print(query)
				staf =True
        
		res = mysqlControl.selectQuery(query)
		print("check schedule query", res)
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
								print("log res query1", logRes)
								sm.current = "endF"
					else:
						logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_gagal','{self.nik}')"
                    
						logRes = mysqlControl.CUDQuery(logQuery)
						print("log res query2",logRes)
						self.manager.ids.EndWindowFail.msgId.text = '[color=000000]Maaf, schedule anda tidak ditemukan pada database[/color]'
						sm.current = "endF"
				else:
					if(len(res) == 0):
						self.manager.ids.EndWindowSuccess.msg.text = '[color=000000]Selamat Datang, [/color]'
						logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_sukses','{self.nik}')"
                    
						logRes = mysqlControl.CUDQuery(logQuery)
						print('log res query s1',logRes)
						sm.current = "endS"
					else:
						startTime = res[0][1]
						timeLimit = res[0][0]
						now = datetime.datetime.now()
						now = now.strftime("%Y-%m-%d %H:%M:%S")
						now = datetime.datetime.strptime(now,'%Y-%m-%d %H:%M:%S')
						print(startTime,now,startTime+datetime.timedelta(minutes=timeLimit))
						if(startTime < now < (startTime+datetime.timedelta(minutes=timeLimit))):
								self.manager.ids.EndWindowSuccess.msg.text = f'[color=000000]Selamat Datang, {res[0][2]}[/color]'
								logQuery = f"insert into access_log values ('{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}','','masuk_sukses','{self.nik}')"
								logRes = mysqlControl.CUDQuery(logQuery)
								print('log res query s2',logRes)
								sm.current = "endS"
						else:
							self.manager.ids.EndWindowFail.msgId.text = f'[color=000000]Maaf, anda sudah melewati durasi limit guess anda {startTime+datetime.timedelta(minutes=timeLimit)} [/color]'
							sm.current = 'endF'
							
                        
                

class RecogWindow(Screen,Image):
	nikk = StringProperty('')
	nama = StringProperty('')
	username = StringProperty('')
	def __init__(self, **kwargs):
		super(RecogWindow, self).__init__(**kwargs)
		self.capture = None
		# self.capture.set(3,480)
		# self.capture.set(3,640)
		#Config.set('graphics', 'maxfps', 30)
		self.fps = 30
		self.countDown =  3
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
		self.countDown =  3
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
		self.countDown =  3
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
						self.countDown = 3
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
		print("recogName :",image_name)
		with open("frame.jpg", "rb") as img_file:
			my_string = base64.b64encode(img_file.read())
			
		my_string = my_string.decode('utf-8')
		print(f"try recog {image_name}")
		request_data = {
			"image_name":image_name,
			"action":"predict",
			"base64_encode":my_string
		}
		#r = requests.post("http://10.0.21.16:10000/api/ImageProcess",json=request_data)
		r = requests.post("https://ai.cosmos.id/api/ImageProcess",json=request_data)
		res = r.json()
		print(res)
		if(res['return_status'] == 'success'):
			return self.nama
		else:
			return "unknown"
        
	def most_frequent(self,List): 
		return max(set(List), key = List.count)
    

    
class EndWindowFail(Screen):
	msgId = ObjectProperty(None)
	def on_enter(self):
		#Config.set('graphics', 'maxfps', 1)
		# subprocess.Popen(["python3","relay_off.py"], stdout=subprocess.PIPE, shell=False)
		Clock.schedule_once(self.backToMain,2)
    
	def backToMain(self,dt):
        
		sm.current = "start"

class EndWindowSuccess(Screen):
	msg = ObjectProperty(None)
	def on_enter(self):
		#Config.set('graphics', 'maxfps', 1)
		subprocess.Popen(["python3","relay_off.py"], stdout=subprocess.PIPE, shell=False)
		Clock.schedule_once(self.backToMain,2)
    
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
