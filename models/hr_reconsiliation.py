from osv import osv, fields

class hr_reconsiliation(osv.osv):

	_name = "hr.recon"

	_columns ={
		"ref_id":fields.char("Reference", size=10, require=True),
		"name":fields.many2one(string="Employee",obj="hr.employee", require=True),
		"date":fields.date("Tanggal"),
	}

hr_reconsiliation()

