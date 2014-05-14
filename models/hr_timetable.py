import math
from osv import osv, fields
from openerp import tools
from openerp.tools.translate import _
from datetime import datetime as dt
import datetime
import netsvc


class hr_timetable(osv.osv):

	_name="hr.timetable"

	_columns={
		"name":fields.char("Name", size=200, required=True, readonly=True, states={"draft":[("readonly", False)]}),
		"date_from":fields.datetime("From", required=True, readonly=True, states={"draft":[("readonly", False)]}),
		"date_to":fields.datetime("To", required=True, readonly=True,states={"draft":[("readonly", False)]}),
		"numbers_of_days":fields.integer("Duration", readonly=True, states={"draft":[("readonly", False)]}),
		"state":fields.selection(selection=[("draft", "Draft"),("confirm", "Confirm"), ("approve", "Approve"), ("cancel", "Cancel")], string="State", readonly=True),
		"notes":fields.text("Notes", readonly=True, states={"draft":[("readonly", False)]}),
		"parent_id":fields.many2one("hr.employee","Manager/Supervisor", readonly=True,states={"draft":[("readonly", False)]}),
		"personil":fields.many2many(string="Persons", obj="hr.employee", id1="person_ids", id2="person_det_id", required=True, readonly=True,states={"draft":[("readonly", False)]}),
		"work_pattern":fields.one2many("hr.work_pattern","pattern_id","Work Patterns", required=True, readonly=True, states={"draft":[("readonly", False)]}),
		"create_by":fields.many2one(string="Create By", obj="res.users", readonly=True),
		"create_time":fields.date(string="Created At", readonly=True),
		"confirm_by":fields.many2one(string="Confirm By", obj="res.users", readonly=True),
		"confirm_time":fields.date(string="Confirm At", readonly=True),
		"approve_by":fields.many2one(string="Approve By", obj="res.users", readonly=True),
		"approve_time":fields.date(string="Approve At", readonly=True),
        "cancel_by":fields.many2one(string="Cancel By", obj="res.users", readonly=True),
		"cancel_time":fields.date(string="Cancel At", readonly=True),

	}

	def _get_number_of_days(self, date_from, date_to):
		DATEFORMAT = "%Y-%m-%d %H:%M:%S"
		
		#str_date_from ="%s 00:00:00"%(date_from)
		#str_date_to ="%s 00:00:00"%(date_to)


		from_date = dt.strptime(date_from, DATEFORMAT)
		to_date = dt.strptime(date_to, DATEFORMAT)

		timedelta = to_date - from_date
		diff_day = timedelta.days + float(timedelta.seconds)/86400

		return diff_day

	def onchange_date_from(self, cr, uid, ids, date_to, date_from):
		
		if(date_from and date_to) and(date_from >date_to):
			raise osv.except_osv(
				_("Warning!"),

				_("The start date must be anterior to the end date")
			)
		result = {"value":{}}

		if date_from and not date_to:
			#str_date_from ="%s 08:00:00"%(date_from)
			date_to_with_delta = dt.strptime(date_from, tools.DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(hours=8)

			date_to_normal = dt.strftime(date_to_with_delta,"%Y-%m-%d")
			result["value"]["date_to"] = str(date_to_with_delta)

		if(date_to and date_from) and (date_from <= date_to):
			diff_day = self._get_number_of_days(date_from, date_to)
			result["value"]["numbers_of_days"] = round(math.floor(diff_day)) + 1
		else:
			result["value"]["numbers_of_days"] = 0

		return result
	
	def onchange_date_to(self, cr, uid, ids, date_to, date_from):
		
		if(date_from and date_to) and(date_from >date_to):
			raise osv.except_osv(
				_("Warning!"),
				_("The start date must be anterior to the end date")
			)
		result = {"value":{}}

		if(date_to and date_from) and (date_from <= date_to):
			diff_day = self._get_number_of_days(date_from, date_to)
			result["value"]["numbers_of_days"] = round(math.floor(diff_day)) + 1
		else:
			result["value"]["numbers_of_days"] = 0
		return result
	
	def action_set_draft(self, cr, uid, ids, context={}):
		
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

	def action_cancel(self, cr, uid, ids, context={}):
		wkf_service = netsvc.LocalService("workflow")

		for id in ids:
			if not self.delete_workflow_instance(cr, uid, id):return False
			if not self.create_workflow_instance(cr, uid, id):return False

			wkf_service.trg_validate(uid, "hr.timetable", id, "button_cancel", cr)

		return True

	def workflow_action_confirm(self, cr, uid, ids, context={}):
		for id in ids:
			if not self.log_audit(cr, uid, id, "confirm"):
				return False
		return True

	def workflow_action_approve(self, cr, uid, ids, context={}):
		for id in ids:
			if not self.log_audit(cr, uid, id , "approve"):return False
		return True

	def workflow_action_cancel(self, cr, uid, ids, context={}):
		for id in ids:
			if not self.log_audit(cr, uid, id, "cancel"):return False
		return True

	def create_workflow_instance(self, cr, uid, id):
		wkf_service = netsvc.LocalService("workflow")
		wkf_service.trg_create(uid, "hr.timetable", id, cr)

		return True

	def delete_workflow_instance(self, cr, uid, id):
		wkf_service = netsvc.LocalService("workflow")
		wkf_service.trg_delete(uid, "hr.timetable", id, cr)

		return True

	def clear_log(self, cr, uid, id):
		vals = {
				
				"create_by":False,
				"create_time":False,
				"confirm_by":False,
				"confirm_time":False,
				"approve_by":False,
				"approve_time":False,
				"cancel_by":False,
				"cancel_time":False
				}
		self.write(cr, uid, [id], vals)

		return True

	def log_audit(self, cr, uid, id, state):

		if state not in ["create", "confirm", "approve", "cancel"]:
			raise osv.except_osv(
					_("Warning !"),
					_("Undifined Method Log Audit")
				)
			return False

		state_dict = {
					"create":"draft",
					"confirm":"confirm",
					"approve":"approve",
					"cancel":"cancel",
				}
		
		vals ={
				"%s_by"%(state):uid,
				"%s_time"%(state):dt.now().strftime("%Y-%m-%d"),
				"state":state_dict.get(state, False),
			}

		self.write(cr, uid, [id], vals)
		return True

	def default_state(self, cr, uid, context={}):
		return "draft"

	_defaults = {
		"state":default_state		
	}

hr_timetable()

class hr_personil(osv.osv):

	_name="hr.persons"

	_columns = {
			"person_ids":fields.many2one("hr.timetable", "Person"),		
	}
hr_personil()

class hr_work_pattern(osv.osv):

	_name="hr.work_pattern"
	_columns = {
			"sequence":fields.integer("Sequence", required=True),
			"pattern_id":fields.many2one("hr.timetable", "Pattern"),
			"name":fields.selection(selection=[("1","Senin"),("2","Selasa"),("3", "Rabu"), ("4","Kamis"),("5", "Jumat"),("6", "Sabtu"),("7", "Minggu")], string="Day", required=True),
			"work_start":fields.float("Start", digits=(2,2)),
			"work_end":fields.float("End", digits=(2,2)),
			"rest_start":fields.float("Rest Start", digits=(2,2)),
			"rest_end":fields.float("Rest End", digits=(2,2)),
			"tolerance":fields.integer("Atendance Tolerance")
	
		}

	def default_sequence(cr, uid, ids, context={}):
		return "7"
	_defaults = {
		"sequence":default_sequence		
	}
hr_work_pattern()
