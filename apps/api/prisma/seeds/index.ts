import { PrismaClient, PermissionAction } from '@prisma/client';
import * as bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

const MODULES = [
  'students', 'teachers', 'classes', 'subjects', 'attendance', 'grades',
  'examinations', 'finance', 'hr', 'admissions', 'library', 'transport',
  'hostel', 'reports', 'ai', 'automation', 'settings', 'notifications',
  'inventory', 'cms', 'audit', 'analytics', 'clinic', 'backup',
  'integrations', 'customization', 'communications', 'documents',
  'lms', 'timetable', 'results',
];

const RESOURCES: Record<string, string[]> = {
  students: ['students'],
  teachers: ['teachers'],
  classes: ['classes'],
  subjects: ['subjects'],
  attendance: ['attendance'],
  grades: ['grades'],
  examinations: ['examinations'],
  finance: ['fee-structures', 'invoices', 'payments', 'expenses', 'gateways', 'reports', 'debtors', 'scholarships'],
  hr: ['staff', 'leave', 'payroll'],
  admissions: ['admissions'],
  library: ['library'],
  transport: ['transport'],
  hostel: ['hostel'],
  reports: ['reports'],
  ai: ['ai'],
  automation: ['automation'],
  settings: ['settings', 'roles'],
  notifications: ['notifications', 'announcements'],
  inventory: ['inventory'],
  cms: ['pages', 'news', 'events'],
  audit: ['audit'],
  analytics: ['analytics'],
  clinic: ['clinic'],
  backup: ['backup'],
  integrations: ['integrations'],
  customization: ['customization'],
  communications: ['messages', 'broadcasts'],
  documents: ['documents'],
  lms: ['courses'],
  timetable: ['timetable'],
  results: ['results'],
};

const ACTIONS: PermissionAction[] = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT', 'EXPORT', 'IMPORT', 'MANAGE'];

const ROLE_PERMISSIONS: Record<string, string[]> = {
  'super-admin': ['*'],
  'school-owner': ['*'],
  'director': ['*'],
  'principal': [
    'students:*', 'teachers:*', 'classes:*', 'subjects:*', 'attendance:*',
    'grades:*', 'examinations:*', 'finance:*', 'hr:*', 'admissions:*',
    'reports:*', 'ai:*', 'settings:settings:READ',
    'audit:audit:READ', 'analytics:analytics:READ', 'clinic:clinic:READ',
    'communications:*', 'documents:documents:*', 'lms:courses:*',
    'timetable:timetable:*', 'results:results:*',
  ],
  'vice-principal': [
    'students:*', 'teachers:*', 'classes:*', 'subjects:*', 'attendance:*',
    'grades:*', 'examinations:*', 'admissions:*', 'reports:*',
    'analytics:analytics:READ', 'communications:*', 'documents:documents:READ',
    'lms:courses:READ', 'timetable:timetable:*', 'results:results:*',
  ],
  'academic-administrator': [
    'students:students:READ', 'students:students:UPDATE',
    'classes:*', 'subjects:*', 'attendance:*', 'grades:*', 'examinations:*',
    'admissions:*', 'reports:reports:READ',
    'lms:courses:*', 'timetable:timetable:*', 'results:results:*',
    'documents:documents:READ',
  ],
  'admission-officer': [
    'admissions:*', 'students:students:CREATE', 'students:students:READ',
  ],
  'examination-officer': [
    'examinations:*', 'grades:*', 'students:students:READ',
    'results:results:*',
  ],
  'bursar': [
    'finance:*', 'reports:reports:READ', 'analytics:analytics:READ',
    'documents:documents:READ',
  ],
  'accountant': [
    'finance:invoices:READ', 'finance:payments:CREATE', 'finance:payments:READ',
    'finance:expenses:*', 'finance:reports:READ', 'finance:debtors:READ',
  ],
  'hr-manager': [
    'hr:*', 'reports:reports:READ', 'documents:documents:READ',
    'communications:messages:*',
  ],
  'teacher': [
    'students:students:READ', 'attendance:attendance:CREATE', 'attendance:attendance:READ',
    'grades:grades:CREATE', 'grades:grades:READ', 'grades:grades:UPDATE',
    'classes:classes:READ', 'subjects:subjects:READ',
    'lms:courses:*', 'timetable:timetable:READ', 'results:results:*',
    'communications:messages:*', 'documents:documents:READ',
  ],
  'class-teacher': [
    'students:students:READ', 'students:students:UPDATE',
    'attendance:attendance:CREATE', 'attendance:attendance:READ',
    'grades:grades:CREATE', 'grades:grades:READ', 'grades:grades:UPDATE',
    'classes:classes:READ', 'subjects:subjects:READ',
    'notifications:notifications:CREATE', 'notifications:announcements:CREATE',
    'lms:courses:*', 'timetable:timetable:READ', 'results:results:*',
    'communications:messages:*', 'communications:broadcasts:CREATE',
    'documents:documents:READ',
  ],
  'librarian': ['library:*'],
  'transport-manager': ['transport:*'],
  'hostel-manager': ['hostel:*'],
  'parent': [
    'students:students:READ', 'attendance:attendance:READ',
    'grades:grades:READ', 'finance:invoices:READ', 'notifications:notifications:READ',
    'results:results:READ', 'timetable:timetable:READ',
  ],
  'student': [
    'grades:grades:READ', 'attendance:attendance:READ',
    'notifications:notifications:READ',
    'lms:courses:READ', 'timetable:timetable:READ', 'results:results:READ',
  ],
};

async function main() {
  console.log('🌱 Seeding EduCore database...');

  // 1. Create School
  const school = await prisma.school.upsert({
    where: { code: 'DEMO001' },
    update: {},
    create: {
      name: 'EduCore Demo School',
      code: 'DEMO001',
      slug: 'educore-demo',
      email: 'admin@educore.ng',
      phone: '+2348000000000',
      address: '1 Education Avenue',
      city: 'Lagos',
      state: 'Lagos',
      country: 'Nigeria',
      timezone: 'Africa/Lagos',
      currency: 'NGN',
      currencySymbol: '₦',
      isActive: true,
      isVerified: true,
    },
  });
  console.log(`✅ School: ${school.name} (${school.id})`);

  // 2. Create Permissions
  const allPermissions: { module: string; resource: string; action: PermissionAction }[] = [];
  for (const [module, resources] of Object.entries(RESOURCES)) {
    for (const resource of resources) {
      for (const action of ACTIONS) {
        allPermissions.push({ module, resource, action });
      }
    }
  }

  for (const perm of allPermissions) {
    await prisma.permission.upsert({
      where: { module_resource_action: perm },
      update: {},
      create: perm,
    });
  }
  console.log(`✅ Created ${allPermissions.length} permissions`);

  const allPermissionsDb = await prisma.permission.findMany();
  const permMap = new Map(allPermissionsDb.map((p) => [`${p.module}:${p.resource}:${p.action}`, p.id]));

  // 3. Create Roles
  const rolesData = Object.keys(ROLE_PERMISSIONS).map((slug) => ({
    slug,
    name: slug.split('-').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
    isSystem: true,
    schoolId: school.id,
    color: getDefaultColor(slug),
  }));

  for (const roleData of rolesData) {
    const role = await prisma.role.upsert({
      where: { schoolId_slug: { schoolId: school.id, slug: roleData.slug } },
      update: {},
      create: roleData,
    });

    // Assign permissions
    const perms = ROLE_PERMISSIONS[roleData.slug];
    if (perms.includes('*')) {
      // All permissions
      for (const perm of allPermissionsDb) {
        await prisma.rolePermission.upsert({
          where: { roleId_permissionId: { roleId: role.id, permissionId: perm.id } },
          update: {},
          create: { roleId: role.id, permissionId: perm.id },
        });
      }
    } else {
      for (const permPattern of perms) {
        const [module, resource, action] = permPattern.split(':');
        for (const perm of allPermissionsDb) {
          const moduleMatch = module === '*' || perm.module === module;
          const resourceMatch = !resource || resource === '*' || perm.resource === resource;
          const actionMatch = !action || action === '*' || perm.action === action;
          if (moduleMatch && resourceMatch && actionMatch) {
            await prisma.rolePermission.upsert({
              where: { roleId_permissionId: { roleId: role.id, permissionId: perm.id } },
              update: {},
              create: { roleId: role.id, permissionId: perm.id },
            });
          }
        }
      }
    }
  }
  console.log(`✅ Created ${rolesData.length} roles with permissions`);

  // 4. Create Academic Year & Terms
  const academicYear = await prisma.academicYear.upsert({
    where: { schoolId_name: { schoolId: school.id, name: '2024/2025' } },
    update: { isCurrent: true },
    create: {
      schoolId: school.id,
      name: '2024/2025',
      startDate: new Date('2024-09-01'),
      endDate: new Date('2025-07-31'),
      isCurrent: true,
    },
  });

  const terms = [
    { name: 'First Term', type: 'FIRST_TERM' as any, startDate: '2024-09-01', endDate: '2024-12-20', isCurrent: false },
    { name: 'Second Term', type: 'SECOND_TERM' as any, startDate: '2025-01-13', endDate: '2025-04-11', isCurrent: true },
    { name: 'Third Term', type: 'THIRD_TERM' as any, startDate: '2025-04-28', endDate: '2025-07-25', isCurrent: false },
  ];

  for (const termData of terms) {
    await prisma.term.upsert({
      where: { academicYearId_type: { academicYearId: academicYear.id, type: termData.type } },
      update: {},
      create: {
        academicYearId: academicYear.id,
        name: termData.name,
        type: termData.type,
        startDate: new Date(termData.startDate),
        endDate: new Date(termData.endDate),
        isCurrent: termData.isCurrent,
      },
    });
  }
  console.log(`✅ Academic year and terms created`);

  // 5. Create Departments
  const deptNames = ['Sciences', 'Arts', 'Commercial', 'Languages', 'Social Sciences', 'Administration'];
  for (const name of deptNames) {
    await prisma.department.upsert({
      where: { schoolId_name: { schoolId: school.id, name } },
      update: {},
      create: { schoolId: school.id, name },
    });
  }

  // 6. Create Classes
  const classesData = [
    { name: 'JSS 1', section: 'A', level: 7, capacity: 35 },
    { name: 'JSS 1', section: 'B', level: 7, capacity: 35 },
    { name: 'JSS 2', section: 'A', level: 8, capacity: 35 },
    { name: 'JSS 2', section: 'B', level: 8, capacity: 35 },
    { name: 'JSS 3', section: 'A', level: 9, capacity: 35 },
    { name: 'JSS 3', section: 'B', level: 9, capacity: 35 },
    { name: 'SS 1', section: 'Science', level: 10, capacity: 35 },
    { name: 'SS 1', section: 'Arts', level: 10, capacity: 35 },
    { name: 'SS 2', section: 'Science', level: 11, capacity: 35 },
    { name: 'SS 2', section: 'Arts', level: 11, capacity: 35 },
    { name: 'SS 3', section: 'Science', level: 12, capacity: 35 },
    { name: 'SS 3', section: 'Arts', level: 12, capacity: 35 },
  ];

  for (const cls of classesData) {
    await prisma.classRoom.upsert({
      where: { schoolId_name_section: { schoolId: school.id, name: cls.name, section: cls.section || '' } },
      update: {},
      create: { schoolId: school.id, ...cls },
    });
  }
  console.log(`✅ Created ${classesData.length} classes`);

  // 7. Create Subjects
  const subjectsData = [
    'Mathematics', 'English Language', 'Physics', 'Chemistry', 'Biology',
    'Further Mathematics', 'Economics', 'Government', 'Literature in English',
    'Geography', 'History', 'Agricultural Science', 'Computer Science',
    'French', 'Yoruba', 'Civic Education', 'Basic Technology',
    'Business Studies', 'Physical and Health Education',
  ];

  for (const name of subjectsData) {
    await prisma.subject.upsert({
      where: { schoolId_name: { schoolId: school.id, name } },
      update: {},
      create: { schoolId: school.id, name },
    });
  }

  // 8. Create Admin User
  const adminPasswordHash = await bcrypt.hash('Admin2024!', 12);
  const superAdminRole = await prisma.role.findFirst({ where: { schoolId: school.id, slug: 'super-admin' } });

  const adminUser = await prisma.user.upsert({
    where: { email: 'admin@educore.ng' },
    update: {},
    create: {
      email: 'admin@educore.ng',
      passwordHash: adminPasswordHash,
      firstName: 'Super',
      lastName: 'Admin',
      status: 'ACTIVE',
      emailVerified: true,
      emailVerifiedAt: new Date(),
      schoolId: school.id,
    },
  });

  if (superAdminRole) {
    await prisma.userRole.upsert({
      where: { userId_roleId: { userId: adminUser.id, roleId: superAdminRole.id } },
      update: {},
      create: { userId: adminUser.id, roleId: superAdminRole.id },
    });
  }

  // 9. Create Principal user
  const principalHash = await bcrypt.hash('Principal2024!', 12);
  const principalRole = await prisma.role.findFirst({ where: { schoolId: school.id, slug: 'principal' } });
  const principalUser = await prisma.user.upsert({
    where: { email: 'principal@educore.ng' },
    update: {},
    create: {
      email: 'principal@educore.ng',
      passwordHash: principalHash,
      firstName: 'Dr. Amaka',
      lastName: 'Okonkwo',
      status: 'ACTIVE',
      emailVerified: true,
      emailVerifiedAt: new Date(),
      schoolId: school.id,
    },
  });
  if (principalRole) {
    await prisma.userRole.upsert({
      where: { userId_roleId: { userId: principalUser.id, roleId: principalRole.id } },
      update: {},
      create: { userId: principalUser.id, roleId: principalRole.id },
    });
  }

  // 10. Create Staff + Teacher
  const teacherHash = await bcrypt.hash('Teacher2024!', 12);
  const teacherRole = await prisma.role.findFirst({ where: { schoolId: school.id, slug: 'teacher' } });
  const teacherUser = await prisma.user.upsert({
    where: { email: 'teacher@educore.ng' },
    update: {},
    create: {
      email: 'teacher@educore.ng',
      passwordHash: teacherHash,
      firstName: 'Mr. Emeka',
      lastName: 'Adeyemi',
      gender: 'MALE',
      status: 'ACTIVE',
      emailVerified: true,
      emailVerifiedAt: new Date(),
      schoolId: school.id,
    },
  });

  const teacherStaff = await prisma.staff.upsert({
    where: { schoolId_staffId: { schoolId: school.id, staffId: 'STF2401' } },
    update: {},
    create: {
      userId: teacherUser.id,
      schoolId: school.id,
      staffId: 'STF2401',
      position: 'Mathematics Teacher',
      employmentType: 'FULL_TIME',
      joiningDate: new Date('2020-09-01'),
      salary: 120000,
    },
  });

  const teacher = await prisma.teacher.upsert({
    where: { staffId: teacherStaff.id },
    update: {},
    create: { staffId: teacherStaff.id },
  });

  if (teacherRole) {
    await prisma.userRole.upsert({
      where: { userId_roleId: { userId: teacherUser.id, roleId: teacherRole.id } },
      update: {},
      create: { userId: teacherUser.id, roleId: teacherRole.id },
    });
  }

  // 11. Create demo Student
  const studentHash = await bcrypt.hash('Student2024!', 12);
  const studentRole = await prisma.role.findFirst({ where: { schoolId: school.id, slug: 'student' } });
  const studentUser = await prisma.user.upsert({
    where: { email: 'student@educore.ng' },
    update: {},
    create: {
      email: 'student@educore.ng',
      passwordHash: studentHash,
      firstName: 'Chidera',
      lastName: 'Obi',
      gender: 'MALE',
      dateOfBirth: new Date('2008-03-15'),
      status: 'ACTIVE',
      emailVerified: true,
      emailVerifiedAt: new Date(),
      schoolId: school.id,
    },
  });

  const student = await prisma.student.upsert({
    where: { schoolId_admissionNo: { schoolId: school.id, admissionNo: 'STU240001' } },
    update: {},
    create: {
      userId: studentUser.id,
      schoolId: school.id,
      admissionNo: 'STU240001',
      nationality: 'Nigerian',
    },
  });

  const firstClass = await prisma.classRoom.findFirst({ where: { schoolId: school.id, name: 'SS 2', section: 'Science' } });
  if (firstClass) {
    await prisma.studentEnrollment.upsert({
      where: { studentId_classRoomId_academicYearId: { studentId: student.id, classRoomId: firstClass.id, academicYearId: academicYear.id } },
      update: {},
      create: {
        studentId: student.id,
        classRoomId: firstClass.id,
        academicYearId: academicYear.id,
        rollNumber: '001',
        isCurrent: true,
      },
    });
  }

  if (studentRole) {
    await prisma.userRole.upsert({
      where: { userId_roleId: { userId: studentUser.id, roleId: studentRole.id } },
      update: {},
      create: { userId: studentUser.id, roleId: studentRole.id },
    });
  }

  // 12. Create Fee Structure
  const feeStructure = await prisma.feeStructure.upsert({
    where: { id: 'fee-structure-demo' },
    update: {},
    create: {
      id: 'fee-structure-demo',
      schoolId: school.id,
      academicYearId: academicYear.id,
      name: 'SS2 Science - 2nd Term Fees',
      items: {
        create: [
          { name: 'Tuition Fee', amount: 45000 },
          { name: 'Development Levy', amount: 5000 },
          { name: 'Library Fee', amount: 2000 },
          { name: 'ICT Fee', amount: 3000 },
          { name: 'Sports Fee', amount: 2000 },
          { name: 'PTA Levy', amount: 5000, isOptional: true },
        ],
      },
    },
  });

  // 13. Create Library
  await prisma.library.upsert({
    where: { schoolId: school.id },
    update: {},
    create: { schoolId: school.id, name: 'EduCore School Library' },
  });

  // 14. AI Module Configs (disabled by default)
  const aiModules = ['tutor', 'question-generator', 'lesson-planner', 'result-analyzer', 'performance-predictor', 'report-writer', 'chat-assistant'];
  for (const module of aiModules) {
    await prisma.aiModuleConfig.upsert({
      where: { schoolId_module: { schoolId: school.id, module } },
      update: {},
      create: { schoolId: school.id, module, isEnabled: false, config: {} },
    });
  }

  console.log('');
  console.log('🎉 Database seeded successfully!');
  console.log('');
  console.log('📋 Demo Credentials:');
  console.log('  Super Admin : admin@educore.ng       / Admin2024!');
  console.log('  Principal   : principal@educore.ng   / Principal2024!');
  console.log('  Teacher     : teacher@educore.ng     / Teacher2024!');
  console.log('  Student     : student@educore.ng     / Student2024!');
  console.log('');
}

function getDefaultColor(slug: string): string {
  const colors: Record<string, string> = {
    'super-admin': '#7c3aed',
    'school-owner': '#1e40af',
    'principal': '#0f766e',
    'teacher': '#0284c7',
    'student': '#16a34a',
    'parent': '#d97706',
    'bursar': '#be185d',
    'hr-manager': '#7c3aed',
  };
  return colors[slug] || '#64748b';
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
