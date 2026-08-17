# EduCore API Documentation
## Version 1.0 | Base URL: `/api`

All endpoints require `Authorization: Bearer <token>` unless noted.

---

## Authentication

### POST `/auth/login`
Login with email and password.
```json
// Request
{ "email": "admin@school.com", "password": "Password@123" }
// Response
{ "accessToken": "...", "refreshToken": "...", "user": { "id": "...", "role": "..." } }
```

### POST `/auth/refresh`
Refresh access token.
```json
{ "refreshToken": "..." }
```

### POST `/auth/logout`
Invalidate session.

### POST `/auth/forgot-password`
```json
{ "email": "user@school.com" }
```

### POST `/auth/reset-password`
```json
{ "token": "...", "password": "NewPassword@123" }
```

### POST `/auth/mfa/setup`
Enable MFA for current user.

### POST `/auth/mfa/verify`
```json
{ "code": "123456" }
```

---

## Schools

### GET `/schools/:id` — Get school details
### PUT `/schools/:id` — Update school settings
### GET `/schools/:id/stats` — Dashboard statistics

---

## Students

### GET `/students` — List students
Query: `?search=&classRoomId=&status=&page=1&limit=20`

### POST `/students` — Create student
```json
{
  "user": { "firstName": "John", "lastName": "Doe", "email": "john@school.com", "gender": "MALE" },
  "dateOfBirth": "2008-01-15",
  "classRoomId": "cid_...",
  "academicYearId": "ayid_..."
}
```

### GET `/students/:id` — Get student
### PUT `/students/:id` — Update student
### DELETE `/students/:id` — Soft delete student
### GET `/students/:id/attendance` — Student attendance history
### GET `/students/:id/results` — Student results
### GET `/students/:id/invoices` — Student invoices
### POST `/students/:id/promote` — Promote to next class

---

## Teachers

### GET `/teachers` — List teachers
### POST `/teachers` — Create teacher
### GET `/teachers/:id` — Get teacher
### PUT `/teachers/:id` — Update teacher
### GET `/teachers/:id/timetable` — Teacher timetable
### GET `/teachers/:id/classes` — Teacher classes

---

## Classes

### GET `/classes` — List classes
### POST `/classes` — Create class
### GET `/classes/:id` — Get class
### GET `/classes/:id/students` — Students in class
### GET `/classes/:id/subjects` — Subjects for class
### POST `/classes/:id/subjects` — Assign subject to class

---

## Attendance

### GET `/attendance` — List attendance records
Query: `?classRoomId=&date=&status=&studentId=`

### POST `/attendance` — Mark attendance
```json
{
  "classRoomId": "...",
  "date": "2024-01-15",
  "records": [
    { "studentId": "...", "status": "PRESENT" },
    { "studentId": "...", "status": "ABSENT", "remarks": "Sick" }
  ]
}
```

### GET `/attendance/report` — Attendance analytics
### GET `/attendance/student/:id` — Student attendance summary

---

## Finance

### GET `/finance/fee-structures` — List fee structures
### POST `/finance/fee-structures` — Create fee structure
### POST `/finance/invoices/generate` — Generate invoices
```json
{ "feeStructureId": "...", "termId": "...", "studentIds": ["..."] }
```
### GET `/finance/invoices` — List invoices
### GET `/finance/invoices/:id` — Get invoice
### POST `/finance/payments` — Record payment
```json
{ "invoiceId": "...", "amount": 5000, "gateway": "paystack", "reference": "..." }
```
### GET `/finance/payments` — List payments
### GET `/finance/scholarships` — List scholarships
### POST `/finance/scholarships` — Create scholarship
### PUT `/finance/scholarships/:id` — Update scholarship

---

## Results

### GET `/results/grade-scales` — List grade scales
### POST `/results/grade-scales` — Create grade scale
### GET `/results/config` — Get result configuration
### PUT `/results/config` — Update result configuration
### POST `/results/examinations/:examId/results/:studentId` — Enter scores
```json
{
  "scores": {
    "subjectId_1": { "caScore": 35, "examScore": 55 },
    "subjectId_2": { "caScore": 40, "examScore": 50 }
  }
}
```
### GET `/results/examinations/:examId/results` — Get all results for exam
### GET `/results/examinations/:examId/broadsheet?classRoomId=` — Class broadsheet
### POST `/results/examinations/:examId/compute-positions` — Compute class positions
### POST `/results/examinations/:examId/publish` — Publish results
### GET `/results/examinations/:examId/students/:studentId/report-card` — Download PDF

---

## Timetable

### GET `/timetable/classes` — All classes
### GET `/timetable/class/:classRoomId` — Class timetable
### GET `/timetable/teacher/:teacherId` — Teacher timetable
### POST `/timetable/slots` — Create slot
```json
{
  "classRoomId": "...", "subjectId": "...", "teacherId": "...",
  "dayOfWeek": 1, "startTime": "08:00", "endTime": "09:00", "room": "Lab 1"
}
```
### PUT `/timetable/slots/:id` — Update slot
### DELETE `/timetable/slots/:id` — Delete slot

---

## Documents

### GET `/documents/folders` — List folders (query: `?parentId=`)
### POST `/documents/folders` — Create folder
### GET `/documents` — List documents
### POST `/documents` — Add document
### GET `/documents/:id` — Get document
### PUT `/documents/:id` — Update/version document
### PATCH `/documents/:id/move` — Move to folder
### DELETE `/documents/:id` — Delete

---

## Communications

### GET `/communications/broadcasts` — List broadcasts
### POST `/communications/broadcasts` — Create broadcast
### POST `/communications/broadcasts/:id/send` — Send broadcast
### GET `/communications/messages/inbox` — Inbox
### GET `/communications/messages/sent` — Sent messages
### POST `/communications/messages` — Send message
### GET `/communications/messages/:id` — Read message
### GET `/communications/messages/unread-count` — Unread count
### GET `/communications/templates` — List templates
### POST `/communications/templates` — Create template

---

## Parent Portal

### GET `/parent-portal/dashboard` — Parent dashboard summary
### GET `/parent-portal/children` — List children
### GET `/parent-portal/children/:studentId/attendance` — Child attendance
### GET `/parent-portal/children/:studentId/results` — Child results
### GET `/parent-portal/children/:studentId/invoices` — Child invoices
### GET `/parent-portal/notifications` — Parent notifications

---

## HR

### GET `/hr/stats` — HR statistics
### GET `/hr/staff` — List staff
### POST `/hr/staff` — Create staff
### GET `/hr/staff/:id` — Get staff member
### GET `/hr/leave` — List leave requests
### POST `/hr/leave` — Submit leave request
### PUT `/hr/leave/:id/approve` — Approve/reject leave
### GET `/hr/payroll` — List payslips
### POST `/hr/payroll/generate` — Generate payslip
### GET `/hr/salary-structures` — List salary structures
### POST `/hr/salary-structures` — Create salary structure
### GET `/hr/performance-reviews` — List reviews
### POST `/hr/performance-reviews` — Create review

---

## Inventory

### GET `/inventory/stats` — Inventory statistics
### GET `/inventory/items` — List items (query: `?search=&categoryId=&isAsset=`)
### POST `/inventory/items` — Create item
### PUT `/inventory/items/:id` — Update item
### POST `/inventory/items/:id/transactions` — Record stock transaction
```json
{ "type": "IN", "quantity": 50, "notes": "Purchased from supplier" }
```
### GET `/inventory/low-stock` — Low stock alerts
### GET `/inventory/categories` — List categories
### GET `/inventory/suppliers` — List suppliers

---

## Clinic

### GET `/clinic/stats` — Clinic statistics
### GET `/clinic/visits` — List visits
### POST `/clinic/visits` — Log visit
### GET `/clinic/records/student/:studentId` — Student medical record
### POST `/clinic/records` — Create/update medical record

---

## Analytics

### GET `/analytics/dashboard` — Executive dashboard
### GET `/analytics/revenue?year=&months=` — Revenue analytics
### GET `/analytics/students` — Student analytics
### GET `/analytics/attendance?weeks=` — Attendance trends
### GET `/analytics/academic` — Academic performance
### GET `/analytics/finance?from=&to=` — Finance report
### GET `/analytics/export/:type` — Export to Excel (types: `finance`, `students`, `attendance`)

---

## Audit Logs

### GET `/audit/logs` — List audit logs
Query: `?entity=&userId=&action=&severity=&from=&to=&page=1&limit=50`
### GET `/audit/summary` — Activity summary
### GET `/audit/logs/:entity/:entityId` — Entity change history

---

## Integrations

### GET `/integrations/stats` — Integration statistics
### GET `/integrations/api-keys` — List API keys
### POST `/integrations/api-keys` — Create API key
### DELETE `/integrations/api-keys/:id` — Delete key
### PUT `/integrations/api-keys/:id/revoke` — Revoke key
### GET `/integrations/webhooks` — List webhooks
### POST `/integrations/webhooks` — Create webhook
### POST `/integrations/webhooks/:id/test` — Test webhook
### GET `/integrations/providers` — List all integrations
### PUT `/integrations/providers/:provider` — Configure integration

---

## Customization

### GET `/customization/theme` — Get theme
### PUT `/customization/theme` — Update theme
### GET `/customization/branding` — Get school branding
### PUT `/customization/branding` — Update branding
### GET `/customization/pages` — List custom pages
### PUT `/customization/pages/:slug` — Create/update page
### DELETE `/customization/pages/:slug` — Delete page

---

## Backup

### GET `/backup` — List backups
### GET `/backup/stats` — Backup statistics
### POST `/backup/trigger` — Trigger backup
```json
{ "type": "FULL" }
```

---

## AI Center

### GET `/ai/modules` — List AI modules and status
### PUT `/ai/modules/:key/toggle` — Enable/disable module
### POST `/ai/tutor` — AI tutoring session
### POST `/ai/lesson-plan` — Generate lesson plan
### POST `/ai/question-generator` — Generate questions
### POST `/ai/analyze-performance` — Performance analysis
### POST `/ai/fee-defaulters` — Fee defaulter prediction
### GET `/ai/revenue-forecast` — Revenue forecast
### POST `/ai/admin-report` — Generate admin report
### POST `/ai/generate-communication` — Generate email/SMS
### POST `/ai/chat` — AI chat assistant

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request — validation error |
| 401 | Unauthorized — invalid/expired token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found |
| 409 | Conflict — duplicate record |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Auth endpoints | 10 req/min |
| AI endpoints | 20 req/min |
| General API | 200 req/min |
| File upload | 50 req/min |
