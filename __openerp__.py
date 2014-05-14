{
		"name":"ID HR Timesheet",
		"version":"1.1",
		"author":"IT Prenuer Indonesia, PT",
		"category":"Human Resources",
		"website":"http//itprenuer.com",
		"images":[],
		"description":"""


		""",
		"depends":["l10n_id_hr", "hr_public_holidays"],
		"data":[
			"security/hr_application_data.xml",
			"security/hr_timesheet_groups.xml",
			"security/hr_overtime_groups.xml",
			"security/hr_audit_groups.xml",
			"views/hr_timetable_view.xml",
			"views/hr_employee_calc.xml",
			"views/hr_overtime_view.xml",
			"views/hr_reconsiliation_view.xml",
			"workflow/hr_timesheet_workflow.xml",
			"workflow/hr_overtime_workflow.xml",
			"workflow/hr_audit_workflow.xml",
			"security/ir.model.access.csv"
		],
		"demo":[],
		"installable":True,
		"auto_install":False,
		"application":False,
	
}
