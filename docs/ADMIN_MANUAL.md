# EduCore Administrator Manual

## Getting Started

### First-Time Setup Checklist

After installing EduCore, complete these steps before going live:

1. **Update Admin Password** — Settings → Profile → Change Password
2. **Configure School Information** — Customization → Branding
3. **Set School Theme** — Customization → Theme
4. **Create Academic Year** — Settings → Academic → New Year
5. **Create Terms** — Settings → Academic → Terms
6. **Create Departments** — Settings → Departments
7. **Create Classes** — Classes → New Class
8. **Add Subjects** — Subjects → Add Subject
9. **Assign Subjects to Classes** — Classes → [Class] → Subjects
10. **Configure Fee Structures** — Finance → Fee Structures
11. **Enable Payment Gateways** — Settings → Payments
12. **Configure Grade Scale** — Results → Grade Scales
13. **Add Staff Members** — HR → Staff → Add Staff
14. **Enroll Students** — Students → Add Student
15. **Configure Notifications** — Settings → Notifications

---

## Academic Management

### Creating an Academic Year
1. Go to **Settings → Academic Years**
2. Click **New Academic Year**
3. Enter name (e.g., "2024/2025"), start and end dates
4. Set as current year if applicable

### Managing Classes
- **Create**: Classes → New Class → Enter name, level, section
- **Assign Teacher**: Classes → [Class] → Teacher Assignment
- **Add Students**: Classes → [Class] → Enroll Students
- **Add Subjects**: Classes → [Class] → Subjects

### Timetable Setup
1. Go to **Timetable**
2. Select a class from the dropdown
3. Click any empty cell to add a lesson slot
4. Select subject, teacher, start/end time, and room
5. Conflicts are detected automatically and shown in red

### Examination & Results
1. Create an examination: **Examinations → New Exam**
2. Enter scores: **Results → [Exam] → Enter Scores** (autosaves per cell)
3. Compute positions: Click **Compute Positions** button
4. Publish results: Click **Publish Results** — parents/students are notified
5. Download report cards: Click **📄 Card** on any student row
6. View broadsheet: Toggle to **Broadsheet** tab

---

## Student Management

### Admitting a New Student
1. **Admissions → New Application** (for online workflow)  
   OR **Students → Add Student** (direct admission)
2. Fill in personal information and guardian details
3. Assign to class and academic year
4. Set fee structure — invoice generated automatically
5. Student login credentials are sent via email

### Student Actions
- **Promote**: Student Profile → Promote to Next Class
- **Suspend**: Student Profile → Update Status → Suspended
- **Transfer**: Student Profile → Transfer → Select new class/school
- **Archive/Graduate**: Update Status → Graduated

---

## Finance Management

### Setting Up Fee Structures
1. Finance → Fee Structures → New Structure
2. Add line items (Tuition, Books, Uniform, etc.)
3. Set amounts and which terms apply

### Generating Invoices
1. Finance → Invoices → Generate
2. Select fee structure, term, and student group (class/all)
3. Invoices generated in bulk and visible immediately

### Scholarships & Discounts
1. Finance → Scholarships → New Scholarship
2. Choose type: Percentage or Fixed Amount
3. Assign to individual students or apply school-wide

### Student Debtors
- Finance → Debtors — shows all students with outstanding balances
- Export to Excel for follow-up
- Use Communications to send bulk reminders

### Payment Gateways
1. Settings → Payments → Configure
2. Enable desired gateways
3. Enter API keys and secret keys
4. Set supported currencies and instructions
5. Only enabled gateways appear during student checkout

---

## HR & Payroll

### Adding Staff
1. HR → Staff → Add Staff
2. Enter personal info, qualifications, role, department
3. Assign salary structure
4. Staff portal access is created automatically

### Leave Management
- **View requests**: HR → Leave
- **Approve/Reject**: Click the request → Change status
- Approved leave is reflected in attendance tracking

### Generating Payslips
1. HR → Payslips → Generate Payslip
2. Select staff member, month, and year
3. Payslip is computed from assigned salary structure
4. Download PDF for records

### Salary Structures
1. HR → Payslips → Salary Structures → New Structure
2. Set basic salary, allowances (%), and deductions (%)
3. Net pay is calculated automatically and shown in preview
4. Assign structure to staff in their profile

---

## Communications

### Sending a Broadcast
1. Communications → Broadcasts
2. Write subject and message body
3. Select audience: All, Students, Parents, Staff
4. Choose channels: In-App, Email, SMS
5. Click **Send Now**

### Messaging System
- Inbox/Sent messages work like email within the platform
- Staff and parents can exchange messages
- All messages trigger in-app notifications

### Notification Templates
1. Communications → Templates → New Template
2. Choose type: Email, SMS, Push
3. Write template with variables like `{{studentName}}`, `{{amount}}`
4. Assign template to automated triggers in Automation Center

---

## Document Management

### Folder Structure
- Create a folder hierarchy that mirrors your school's needs
- Suggested: Admissions / Student Records / Staff Files / Circulars / Results
- Folders can be nested unlimited levels

### Uploading Documents
1. Navigate to the target folder
2. Click **Add Document**
3. Enter name, file type, and paste the file URL (Cloudinary/S3)
4. Set access roles (who can see this document)

### Version History
- When updating a document with a new URL, the old version is archived automatically
- Version history is visible in document details

---

## AI Center

### Enabling AI Modules
1. Settings → AI Center
2. Toggle each module on/off individually
3. Requires OpenAI API key in environment config

### Using AI Features
- **AI Tutor**: Dashboard → AI → Tutor — for student homework help
- **Lesson Planner**: AI → Lesson Plan — teachers enter topic, get full plan
- **Question Generator**: AI → Questions — generate exam questions by subject/difficulty
- **Fee Defaulter Predictor**: AI → Analytics — identifies at-risk students
- **Revenue Forecast**: AI → Analytics → Forecast — 3-month revenue projection
- **Report Writer**: AI → Admin Report — generate academic/financial reports
- **Communication Generator**: AI → Generate — draft emails/SMS/announcements

---

## System Configuration

### Roles & Permissions
1. Settings → Roles
2. Default roles come pre-configured
3. Create custom roles: New Role → assign granular permissions
4. Each permission has READ/CREATE/UPDATE/DELETE/MANAGE levels
5. Assign roles to users in their profile

### Integrations
1. Settings → Integrations
2. Enable third-party services (Twilio SMS, SendGrid, Zoom, etc.)
3. Enter API credentials
4. Test connection before going live

### Theme & Branding
1. Customization → Theme
2. Choose a color preset or set custom colors
3. Upload school logo and favicon
4. Set footer text
5. Preview renders live on the right panel
6. Click **Save Theme** — changes apply immediately

### Backup & Recovery
1. Backup → Trigger Full Backup (recommended before major changes)
2. Automated backup: Configure cron job or use cloud scheduler
3. Download backup files from the backup list
4. To restore: use `pg_restore` command with the backup file

---

## Security Best Practices

1. **Change default passwords** immediately after setup
2. **Enable MFA** for admin accounts
3. **Review audit logs** weekly for suspicious activity
4. **Rotate API keys** every 90 days
5. **Set webhook secrets** to verify payload authenticity
6. **Use HTTPS** in production (SSL certificate required)
7. **Restrict database access** — only allow connections from app servers
8. **Regular backups** — automate daily incremental and weekly full backups
9. **Review permissions** — only grant minimum necessary access
10. **Monitor failed logins** — Audit Logs → filter by "login" action

---

## Frequently Asked Questions

**Q: Can I import students in bulk?**
A: Yes — Students → Import → Download template → Fill data → Upload CSV

**Q: Can multiple schools use the same installation?**
A: Yes — EduCore supports multi-school/multi-campus. Each school has isolated data.

**Q: How do I give parents access?**
A: Add parent under Student Profile → Guardians → Add Parent. They receive login credentials automatically.

**Q: Can I customize the report card format?**
A: The report card uses a system-generated PDF. Header info comes from your school branding settings.

**Q: What happens to data when a student graduates?**
A: Set status to "Graduated" — all records are preserved and searchable. Student can no longer log in.

**Q: How does the timetable conflict detection work?**
A: The system checks two conditions: (1) the same class can't have two subjects at the same time slot, (2) a teacher can't be assigned to two classes simultaneously.
