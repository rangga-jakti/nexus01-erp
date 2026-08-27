from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = 'Setup initial HR data'

    @transaction.atomic
    def handle(self, *args, **options):
        from organization.models import Company
        from hr.models import WorkSchedule, LeaveType, PayrollComponent, JobPosition

        company = Company.objects.filter(is_active=True).first()
        if not company:
            self.stdout.write('❌ Run setup_nexus first.')
            return

        self.stdout.write(f'\n🏢 Setup HR for: {company.name}\n')

        # Work Schedules
        for s in [
            ('NORMAL','Jam Kerja Normal','08:00','17:00','12:00','13:00',15,'1,2,3,4,5'),
            ('SHIFT_PAGI','Shift Pagi','06:00','14:00','10:00','10:30',10,'1,2,3,4,5,6'),
            ('SHIFT_SIANG','Shift Siang','14:00','22:00','18:00','18:30',10,'1,2,3,4,5,6'),
            ('WFH','Work From Home','08:00','17:00',None,None,30,'1,2,3,4,5'),
        ]:
            code,name,ws,we,bs,be,tol,wd = s
            obj, created = WorkSchedule.objects.get_or_create(company=company, code=code, defaults={
                'name':name,'work_start':ws,'work_end':we,'break_start':bs,'break_end':be,
                'late_tolerance_minutes':tol,'work_days':wd,'is_active':True})
            self.stdout.write(f'   ✓ {name}')

        # Leave Types
        for lt in [
            ('TAHUNAN','Cuti Tahunan',12,True,True,True,''),
            ('SAKIT','Cuti Sakit',0,True,False,False,''),
            ('MELAHIRKAN','Cuti Melahirkan',90,True,True,False,'F'),
            ('AYAH','Cuti Ayah',2,True,True,False,'M'),
            ('DUKA','Cuti Duka Cita',3,True,False,False,''),
            ('PERNIKAHAN','Cuti Pernikahan',3,True,True,False,''),
            ('TANPABAYAR','Cuti Tanpa Bayar',0,False,True,False,''),
        ]:
            code,name,max_d,paid,req,carry,gender = lt
            obj, created = LeaveType.objects.get_or_create(company=company, code=code, defaults={
                'name':name,'max_days_per_year':max_d,'is_paid':paid,
                'requires_approval':req,'carry_forward':carry,'gender_specific':gender,'is_active':True})
            self.stdout.write(f'   ✓ {name}')

        # Payroll Components
        for comp in [
            ('TJ_MAKAN','Tunjangan Makan','EARNING','FIXED',750000,False,True,1),
            ('TJ_TRANSPORT','Tunjangan Transport','EARNING','FIXED',500000,False,True,2),
            ('TJ_JABATAN','Tunjangan Jabatan','EARNING','PERCENTAGE_BASIC',10,True,False,3),
            ('TJ_KOMUNIKASI','Tunjangan Komunikasi','EARNING','FIXED',200000,False,False,4),
            ('LEMBUR','Upah Lembur','EARNING','FIXED',0,True,False,5),
            ('BPJS_KES_EMP','BPJS Kesehatan (1%)','DEDUCTION','PERCENTAGE_BASIC',1,False,True,1),
            ('BPJS_TK_JHT','BPJS TK - JHT (2%)','DEDUCTION','PERCENTAGE_BASIC',2,False,True,2),
            ('BPJS_TK_JP','BPJS TK - JP (1%)','DEDUCTION','PERCENTAGE_BASIC',1,False,True,3),
            ('PPH21','PPh 21','DEDUCTION','FIXED',0,False,False,4),
            ('KASBON','Potongan Kasbon','DEDUCTION','FIXED',0,False,False,5),
        ]:
            code,name,ctype,calc,amt,taxable,mandatory,order = comp
            obj, created = PayrollComponent.objects.get_or_create(company=company, code=code, defaults={
                'name':name,'component_type':ctype,'calculation_type':calc,
                'default_amount':amt,'is_taxable':taxable,'is_mandatory':mandatory,
                'order':order,'is_active':True})
            self.stdout.write(f'   ✓ {name}')

        # Job Positions
        for pos in [
            ('DIR','Direktur',20000000,50000000),
            ('MGR','Manager',10000000,20000000),
            ('SPV','Supervisor',6000000,10000000),
            ('STAFF','Staff',4000000,7000000),
            ('IT','IT Staff',5000000,15000000),
            ('ADMIN','Admin',3500000,6000000),
            ('OPS','Operator',3000000,5000000),
            ('INTERN','Magang / Intern',1000000,2000000),
        ]:
            code,name,smin,smax = pos
            obj, created = JobPosition.objects.get_or_create(company=company, code=code, defaults={
                'name':name,'basic_salary_min':smin,'basic_salary_max':smax,'is_active':True})
            self.stdout.write(f'   ✓ {name}')

        self.stdout.write('\n✅ HR setup complete! Buka /hr/employees/ untuk tambah karyawan.\n')
