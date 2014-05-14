from osv import fields, osv
from datetime import date, datetime
import decimal_precision as dp
import netsvc

class hr_overtime(osv.osv):

	_name="hr.overtime"
	_columns ={
				"name":fields.char("Overtime Request", size=200, required=True),
				"employee_id":fields.many2one(string="Employee", obj="hr.employee", required=True, readonly=True, states={"draft":[("readonly", False)]}),
				"date_request":fields.date(string="Date Request", required=True, readonly=True, states={"draft":[("readonly", False)]}),
				"hour_start":fields.float(string="From ", readonly=True, digits=(2,2),states={"draft":[("readonly", False)]}),
				"hour_end":fields.float(string="Until", readonly=True,  digits=(2,2),states={"draft":[("readonly", False)]}),
				"duration":fields.integer(string="Duration", readonly=True),
				"desc":fields.text("Keterangan"),
				"state":fields.selection(selection=[("draft", "Draft"),("confirm", "Confirm"), ("approve", "Approve"), ("cancel", "Cancel"), ("done","Done")], string="Status", readonly=True),
				"create_by":fields.many2one(string="Create By", obj="res.users", readonly=True),
				"create_time":fields.datetime(string="Created Time", readonly=True),
				"confirm_time":fields.datetime(string="Confirmed Time", readonly=True),
				"confirm_by":fields.many2one(string="Confirmed By", obj="res.users", readonly=True),
				"approve_by":fields.many2one(string="Approve By", obj="res.users", readonly=True),				
				"approve_time":fields.datetime(string="Approve Time", readonly=True),

				#"process_by":fields.many2one(string="Process By", obj="res.users", readonly=True),
				#"process_time":fields.datetime(string="Process Time", readonly=True),

				"cancel_by":fields.many2one(string="Cancel By", obj="res.users", readonly=True),
				"cancel_time":fields.datetime(string="Canceled Time", readonly=True),
				"cancel_desc":fields.text("Cancel Reason", readonly=True),

			}
	def default_name(self, cr, uid, context={}):
		return "/"

	def default_state(self, cr, uid, context={}):
		return "draft"

	_defaults ={
			"name":default_name,
			"state":default_state,
			
			}

	def workflow_action_confirm(self, cr, uid, ids, context={}):	
		for id in ids:
			"""
			if not self.create_sequence(cr, uid, id):
				return False
			"""
			if not self.log_audit(cr, uid, id, "confirm"):
				return False
		return True

	def workflow_action_approve(self, cr, uid, ids, context={}):
		for id in ids:
			if not self.log_audit(cr, uid, id, "approve"):
				return False
		return True

	def workflow_action_done(self, cr, uid, ids, context={}):
		for id in ids:
			if not self.log_audit(cr, uid, id, "process"):
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

			wkf_service.trg_validate(uid, "hr.overtime", id, "button_cancel", cr)
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
		wkf_service.trg_create(uid, "hr.overtime", id, cr)
		
		return True
	def delete_workflow_instance(self, cr, uid, id, context={}):
		wkf_service = netsvc.LocalService("workflow")
		wkf_service.trg_delete(uid, "hr.overtime", id, cr)

		return  True

	def clear_log(self, cr, uid, id):
		vals = {
				
					"create_by":False,
					"create_time":False,
					"confirm_by":False,
					"confirm_time":False,
					"process_by":False,
					"process_time":False,
					"approve_by":False,
					"approve_time":False,
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
					"process":"process",
					"cancel":"cancel",
				}

		vals = {
					"%s_by"%(state):uid,
					"%s_time"%(state):datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
					"state":state_dict.get(state, False),
				}


		self.write(cr, uid, [id], vals)
		return True
	
	def create_sequence(self, cr, uid, id):

		sequences = self.pool.get("ir.sequence")
		overtime = self.pool.get("hr.overtime")
		users = self.pool.get("res.users")

		user = users.browse(cr, uid, [uid])[0]
		
		if not user.company_id.sequence_overtime_id:
			raise osv.except_osv("Warning", "Sequence for overtime is unset")
			return False

		sequence_id = user.company_id.sequence_overtime_id.id
		sequence = sequences.next_by_id(cr, uid, sequence_id)

		self.write(cr, uid, [id], {"name":sequence})
		
		return True

hr_overtime()
