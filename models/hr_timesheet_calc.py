from __future__ import division
from osv import osv, fields
from datetime import datetime as dt, date, timedelta
from openerp.tools.translate import _
import netsvc

import sys

try:
	from configparser import ConfigParser
except ImportError:
	from ConfigParser import ConfigParser

import logging
from dateutil.rrule import rrule, DAILY

import datetime
import zkclock
import xlrd
import base64

LOG_DATA_SIZE = 8
logger =logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class hr_audit_timesheet(osv.osv):	
	_name="hr.audit_timesheet_employee"
	_rec_name="ref_id"

	_columns = {
				"ref_id":fields.char(string="References", size=10, required=True, select=True),
				"employee_id":fields.many2one(string="Employee", obj="hr.employee", readonly=True,states={"draft":[("readonly", False)]}),
				"performance_ids":fields.one2many(string="Permormance Analisis", store=False,obj="hr.performance", fields_id="performance_id"),
				"state":fields.selection(selection=[("draft", "Draft"), ("confirm", "Confirm"), ("approve","Approve")], string="State", readonly=True),
				"periode":fields.selection(selection=[("01","January"),("02","February"),("03", "March"),("04","April"),("05","Mei"),("06","June"),("07","Juli"),("08","August"),("09","September"),("10","October"),("11","November"),("12","December")],string="Periode",readonly=True, required=True,states={"draft":[("readonly",False)]}),
				"mode":fields.selection(selection=[(1, "File"),(2,"Mechine")], string="Mode", readonly=True, states={"draft":[("readonly", False)]}),
				"file":fields.many2one("base.file_import", "Filename"),
				"mechine":fields.many2one("base.address", "Mechine"),
				"year":fields.integer("Year", size=4,required=True),
				"desc":fields.text("Description"),
				"create_by":fields.many2one(string="Create By", obj="res.users", readonly=True),
				"create_time":fields.date(string="Create Time", readonly=True),
				"approve_by":fields.many2one(string="Approve By", obj="res.users", readonly=True),
				"approve_time":fields.date(string="Approve Time", readonly=True),
				"confirm_by":fields.many2one(string="Confirm By", obj="res.users", readonly=True),
				"cancel_by":fields.many2one(string="Cancel By", obj="res.users", readonly=True),
				"cancel_time":fields.date(string="Cancel Time", readonly=True),

			}

	def default_state(self, cr, uid, context={}):
		return "draft"

	def default_mode(self, cr, uid, context={}):
		return 2

	_defaults ={
			"state":default_state,
			"mode":default_mode,
			"periode": lambda *a:dt.now().strftime("%m"),
			"year":lambda *a:int(dt.now().strftime("%Y")),
	}


	def employee_calc(self,cr,uid,ids, employee_id, mode, files, mechine, periode, year,context={}):

		timetables = self.pool.get("hr.timetable")
		employees = self.pool.get("hr.employee")
		overtimes = self.pool.get("hr.overtime")
		public_holidays = self.pool.get("hr.holidays.public")

		#ids = timetables.search(cr, uid, [])

		sql = """SELECT * FROM hr_timetable
			   LEFT OUTER JOIN hr_employee_hr_timetable_rel
			   ON hr_timetable.id = hr_employee_hr_timetable_rel.person_ids
			   LEFT OUTER JOIN hr_persons
			   ON hr_employee_hr_timetable_rel.person_det_id = hr_persons.id
			   WHERE person_det_id=%d AND EXTRACT(MONTH FROM hr_timetable.date_from)=%s 
			   AND EXTRACT(YEAR FROM hr_timetable.date_from)=%d
		"""%(employee_id,periode, year)
		#print sql

		cr.execute(sql)
		ids = map(lambda x: x[0], cr.fetchall())
		
		if len(ids) == 0:
			osv.except_osv(
				"Warning!",
				"User in Timesheet is not configure yet!"
			)
			return False

		timetables_arr = None
		timetables_arr = timetables.browse(cr, uid, ids)[0]

		overtime_by_employee = overtimes.search(cr, uid, [("employee_id","=", employee_id)])
		overtime_data = overtimes.browse(cr,uid,overtime_by_employee)
		public_holidaysbyyear = public_holidays.search(cr, uid, [("year","=",dt.now().year)])

		#host = "192.168.1.201"
		#port = "4370"
		#password = ""
					
		if not timetables_arr:
			osv.except_osv(
				"Warning!",
				"Timesheet is not configure yet!"
			)
			return False

		start_date = dt.strptime(timetables_arr.date_from, "%Y-%m-%d %H:%M:%S").date()
		end_date = dt.strptime(timetables_arr.date_to, "%Y-%m-%d %H:%M:%S").date()
		date_list = [dl.strftime("%Y-%m-%d") for dl in rrule(DAILY, dtstart=start_date, until=end_date)]
	
		if mode != 1:
			address = self.pool.get("base.address").browse(cr, uid, mechine)
			employee_attendance = self.attendance(address.host, address.port, address.auth)
		else:
			data = self.pool.get("base.file_import").browse(cr, uid, files)
			attendances = self.import_excel(data)

		attendance_data = filter(lambda x: employees.browse(cr, uid, employee_id).attendance_code in x, employee_attendance)
	
		swap_in_filtered = []
		swap_out_filtered= []
		vals = []
		values = {}

		for date in date_list:
			temp_filter = filter(lambda log: date in log, attendance_data)
			if temp_filter:
				swap_in_filtered.append(temp_filter[0])
				swap_out_filtered.append(temp_filter[-1])
		
		for swap_in, swap_out in zip(swap_in_filtered, swap_out_filtered):
			for work_pattern in timetables_arr.work_pattern:
				if int(work_pattern.name) == swap_in[0].weekday() + 1:
					tanggal=dt.strftime(swap_in[0], "%Y-%m-%d")
					total_lembur = 0.0
					terlambat = 0.0
					day_type = ""

					workshift_hour = str(int(work_pattern.work_start)).rjust(2,"0")
					workshift_minutes =  str(int(work_pattern.work_start % int(work_pattern.work_start) * 60)).rjust(2,"0")
					workshift_hour_end = str(int(work_pattern.work_end)).rjust(2,"0")
					workshift_minutes_end = str(int(work_pattern.work_end % int(work_pattern.work_end)*60)).rjust(2,"0")
					workshift_starttime = "%s %s:%s:00"%(swap_in[1],workshift_hour, workshift_minutes)	
					workshift_endtime = "%s %s:%s:00"%(tanggal, workshift_hour_end, workshift_minutes_end)

					#work_hours, remainder_end =  divmod((dt.strptime(workshift_endtime, "%Y-%m-%d %H:%M:%S")-dt.strptime(workshift_starttime, "%Y-%m-%d %H:%M:%S")).seconds,3600)

					if((dt.strftime(swap_in[0], "%A")).upper() != "saturday".upper() or dt.strftime(swap_in[0],"%A").upper() != "monday".upper() or not filter(lambda x:swap_in[0] in x, public_holidaysbyyear.read(cr,uid,public_holidays,[]))):
						day_type =  "R"
					elif (dt.strftime(swap_in[0], "%A").upper() == "saturday".upper()):
						day_type ="P"
					elif(dt.strftime(swap_in[0], "%A").upper() == "monday".upper()):
						day_type = "L"
					
					if(swap_in[0] > dt.strptime(workshift_starttime, "%Y-%m-%d %H:%M:%S")):
						hour_start_late_time, remainder_start =  divmod((swap_in[0]-dt.strptime(workshift_starttime, "%Y-%m-%d %H:%M:%S")).seconds,3600)
						minutes_start_late_time, seconds_start = divmod(remainder_start, 60)
						terlambat = "%s:%s:00"%(hour_start_late_time,minutes_start_late_time)
				
					had_overtime = [time for time in overtime_data if time.date_request == tanggal]

					if had_overtime:
						if(dt.strptime(workshift_endtime,"%Y-%m-%d %H:%M:%S") < swap_out[0]):
							overtime_hour, overtime_reminder =  divmod((swap_out[0]-dt.strptime(workshift_endtime,"%Y-%m-%d %H:%M:%S")).seconds, 3600)
							total_lembur = overtime_hour
				
					vals.append((0,0,{
						"tanggal":tanggal,
						"sign_in":str(dt.strftime(swap_in[0],"%H:%M:%S")),
						"sign_out":str(dt.strftime(swap_out[0],"%H:%M:%S")),
						"day_type":day_type,
						"terlambat":terlambat,
						"total_lembur":total_lembur,
					}))

					#print vals

		values.update(performance_ids=vals)

		return {"value":values}			
		
	def attendance(self, host, port, password=""):

		if not zkclock.connect(host, port, password):
			raise osv.except_osv("Warning!", "Connection timeout!")
			return False

		s,r = zkclock.connect(host, port, password)
		r = zkclock.disable(s,r)
		r, userdata = zkclock.get_user_data(s,r)
		r, logdata = zkclock.get_log_data(s,r)
		r = zkclock.enable(s, r) 
		r = zkclock.disconnect(s,r)

		logs = []
		
		if userdata and logdata:
				logdata = zkclock.assemble_log_data_from_packets(logdata)
				users = zkclock.unpack_users_to_dict(userdata)
				logging.debug(users)
		else:
			return False
		
		loglist = []
		while((len(logdata)/LOG_DATA_SIZE) >=1):
			loglist.append(logdata[:LOG_DATA_SIZE])
			logdata = logdata[LOG_DATA_SIZE:]

		for i in loglist:
			log_entry = zkclock.unpack_log(i)
			timestamp = zkclock.decode_time(log_entry.time)
			verification_method = log_entry.decode_verified()
			logs.append([timestamp, timestamp.strftime("%Y-%m-%d"),str(log_entry.uid),verification_method])
		
		return logs

	def import_excel(self, data_file):
		
		 data = base64.decodestring(data_file.file)
		 excel = xlrd.open_workbook(file_contents = data, encoding_override="utf-8")  
		 sh = excel.sheet_by_index(0) 

		 for rx in range(sh.nrows): 
		 	 print [sh.cell(rx, ry).value for ry in range(sh.ncols)]

		 return True

	def workflow_action_confirm(self, cr, uid, ids, context={}):
			for id in ids:
					if not self.log_audit(cr, uid, id,"confirm"):
						return False
			return True

	def workflow_action_approve(self, cr, uid, ids, context={}):
			for id in ids:
				if not self.log_audit(cr, uid, id, "approve"):
					return False
			return True
	def workflow_action_cancel(self, cr, uid, ids, context={}):
			for id in ids:
				if not self.log_audit(cr, uid, id, "cancel"):
					return False
			return True

	def action_cancel(self, cr, uid, ids, context={}):
			wkf_service = netsvc.LocalService("workflow")
			for id in ids:
				if not self.delete_workflow_instance(cr, uid, id):
					return  False
				if not self.create_workflow_instance(cr, uid, id):
					return False

				wkf_service.trg_validate(uid, "hr.audit_timesheet_employee", id, "button_cancel", cr)
			return True
	
	def action_draft(self, cr, uid, ids, context={}):
			for id in ids:
				if not self.delete_workflow_instance(cr, uid, id):
					return False
				if not self.create_workflow_instance(cr, uid, id):
					return False
				if not self.clear_log(cr, uid, id):
					return False
				if not self.log_audit(cr, uid, id, "create"):
					return False
			return True

	def create_workflow_instance(self, cr, uid, id, context={}):
				wkf_service = netsvc.LocalService("workflow")
				wkf_service.trg_create(uid, "hr.audit_timesheet_employee", id, cr)
									
				return True

	def delete_workflow_instance(self, cr, uid, id, context={}):
				wkf_service = netsvc.LocalService("workflow")
				wkf_service.trg_delete(uid, "hr.audit_timesheet_employee", id, cr)

				return  True


	def clear_log(self, cr, uid, id):
			vals ={
						"create_by":False,
						"create_time":False,
						"confirm_by":False,
						"confirm_time":False,
						"approve_by":False,
						"cancel_by":False,
						"cancel_time":False
					}    
			self.write(cr, uid, [id], vals)
			return True
	def log_audit(self, cr, uid, id, state):

			if state not in ["create", "confirm", "approve", "process", "cancel"]:
				raise osv.except_osv(_("Warning!"),_("Undifined Method Log Audit "))
				return False

			state_dict = {
					"create":"draft",
					"confirm":"confirm",
					"approve":"approve",
					"cancel":"cancel",
					}

			vals ={
					"%s_by"%(state):uid,
					"%s_time"%(state):dt.now().strftime("%Y-%m-%d %H:%M:%S"),
					"state":state_dict.get(state, False),

					}
			self.write(cr, uid, [id], vals)
			return True

hr_audit_timesheet()

class base_fileimport(osv.osv):
	_name = "base.file_import"
	_rec_name="name"
	_columns = {
			"name":fields.char("Name", size=100, required=True),
			"file":fields.binary("File", required=True)
			}
base_fileimport()

class base_address(osv.osv):
	_name="base.address"
	_rec_name = "location"
	_columns = {
			"location":fields.char("Location", size=100, required=True),
			"host":fields.char("Host", size=16, required=True),
			"port":fields.integer("Port", size=4, required=True),
			"auth":fields.char("Password", size=10, password=True),
			}
base_address()


class hr_perfromance(osv.osv):

	_name="hr.performance"
	_columns = {
				"performance_id":fields.many2one(string="Performance", obj="hr.audit_timesheet_employee"),
				#"employee_id":fields.many2one(string="Employee", obj="hr.employee", required=True, readonly=True,states={"draft":[("readonly", False)]}),
				"tanggal":fields.date(string="Date"),
				"sign_in":fields.char(string="Swap In"),
				"sign_out":fields.char(string="Swap Out"),
				"day_type":fields.selection(selection=[("L","LIBUR"),("P","PENDEK"),("R","REGULER")], string="Day Type"),
				"terlambat":fields.char(string="Late for Work"),
				"total_lembur":fields.float(string="Overtime Total", digits=(2,2)),
			}

	_defaults = {
				"performance_id": lambda self, cr, uid, context: context.get("active_id", False),
			}
hr_perfromance()
