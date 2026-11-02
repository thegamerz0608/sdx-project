# Non-GUI Core Statement Coverage Report

- **Overall Core Coverage:** **70.30%**
- **Total Executable Statements:** **6148**
- **Total Statements Covered:** **4322**
- **Total Statements Missed:** **1826**

## Package Level Summary

| Package | Statements | Covered | Coverage % |
| :--- | :---: | :---: | :---: |
| `nlp/` | 919 | 810 | **88.1%** |
| `services/` | 3409 | 2294 | **67.3%** |
| `repositories/` | 1472 | 919 | **62.4%** |
| `utils/` | 348 | 299 | **85.9%** |
| `models/` | 0 | 0 | **0.0%** |

## File Level Breakdown

| File | Statements | Missed | Coverage % | Missing Lines |
| :--- | :---: | :---: | :---: | :--- |
| `nlp/__init__.py` | 3 | 0 | 100.0% | `` |
| `nlp/calibration.py` | 123 | 12 | 90.2% | `17, 26, 30, 58, 89, 97, 126...` |
| `nlp/classifiers.py` | 297 | 16 | 94.6% | `22, 25, 32, 35-38, 77, 84, ...` |
| `nlp/dataset_generator.py` | 69 | 4 | 94.2% | `102, 164, 191, 218` |
| `nlp/explainability.py` | 37 | 5 | 86.5% | `17, 35, 61, 86-87` |
| `nlp/feature_extractor.py` | 35 | 4 | 88.6% | `28, 47, 55, 61` |
| `nlp/model_evaluator.py` | 94 | 28 | 70.2% | `28, 56, 108, 133, 136-139, ...` |
| `nlp/oov_detector.py` | 75 | 14 | 81.3% | `35, 51, 62, 67, 84, 94-97, ...` |
| `nlp/preprocessor.py` | 55 | 8 | 85.5% | `69, 90, 92, 97, 101, 116, 1...` |
| `nlp/vectorizer.py` | 131 | 18 | 86.3% | `35, 52, 54, 76, 96, 98, 101...` |
| `repositories/__init__.py` | 4 | 0 | 100.0% | `` |
| `repositories/attendance_repository.py` | 80 | 23 | 71.2% | `94, 142-147, 162, 167, 172,...` |
| `repositories/audit_repository.py` | 103 | 21 | 79.6% | `26, 99, 133-134, 138-140, 1...` |
| `repositories/department_repository.py` | 77 | 41 | 46.8% | `92, 112-116, 119-121, 123, ...` |
| `repositories/faculty_repository.py` | 118 | 62 | 47.5% | `387, 421-423, 429-434, 442-...` |
| `repositories/grace_repository.py` | 125 | 54 | 56.8% | `72, 83, 112-116, 118-120, 1...` |
| `repositories/instructor_repository.py` | 129 | 51 | 60.5% | `160, 189-190, 193-195, 201-...` |
| `repositories/leave_application_repository.py` | 187 | 60 | 67.9% | `87, 101-102, 118-122, 141, ...` |
| `repositories/leave_repository.py` | 111 | 52 | 53.2% | `106, 116-121, 127, 136-141,...` |
| `repositories/settings_repository.py` | 66 | 22 | 66.7% | `45, 53, 56, 63-64, 68-75, 8...` |
| `repositories/stationery_repository.py` | 84 | 26 | 69.0% | `87, 95, 131-136, 149, 169-1...` |
| `repositories/student_marks_repository.py` | 91 | 26 | 71.4% | `124, 127-128, 136, 166-167,...` |
| `repositories/student_repository.py` | 97 | 38 | 60.8% | `75, 110-116, 141-145, 155-1...` |
| `repositories/substitute_repository.py` | 141 | 56 | 60.3% | `63, 72-73, 88-92, 111, 146-...` |
| `repositories/user_repository.py` | 59 | 21 | 64.4% | `378, 410-414, 416-417, 436,...` |
| `services/__init__.py` | 3 | 0 | 100.0% | `` |
| `services/analytics_service.py` | 68 | 5 | 92.6% | `25, 52, 85, 96, 132` |
| `services/attendance_service.py` | 52 | 13 | 75.0% | `26, 31, 37-40, 50, 54, 57, ...` |
| `services/audit_service.py` | 42 | 9 | 78.6% | `29, 51, 70, 192, 198, 207-2...` |
| `services/auth_service.py` | 111 | 17 | 84.7% | `81, 85, 89, 97, 101, 117, 1...` |
| `services/backup_service.py` | 341 | 58 | 83.0% | `47-53, 73, 82, 90, 93, 98, ...` |
| `services/department_service.py` | 52 | 19 | 63.5% | `23, 27, 31, 36, 42, 45, 67-...` |
| `services/email_service.py` | 111 | 44 | 60.4% | `51, 55-58, 62-63, 65, 75, 1...` |
| `services/faculty_service.py` | 80 | 31 | 61.3% | `29, 42, 47, 50, 54, 59, 64,...` |
| `services/grace_service.py` | 72 | 21 | 70.8% | `28, 33, 67, 70, 87, 92, 95,...` |
| `services/instructor_service.py` | 85 | 22 | 74.1% | `29, 38, 40, 45, 48, 51, 56,...` |
| `services/leave_service.py` | 114 | 33 | 71.1% | `30, 35, 66, 80, 90, 95, 101...` |
| `services/leave_workflow_service.py` | 257 | 50 | 80.5% | `47, 51, 60, 73-74, 78, 85, ...` |
| `services/mobile_punch_service.py` | 396 | 189 | 52.3% | `17, 22, 50, 56-57, 59, 75, ...` |
| `services/model_training_service.py` | 123 | 10 | 91.9% | `42, 126, 139, 141-142, 145,...` |
| `services/nlp_service.py` | 46 | 9 | 80.4% | `24, 26-27, 34-37, 40, 44` |
| `services/public_tunnel_manager.py` | 245 | 201 | 18.0% | `25, 30, 47, 50-52, 59-60, 6...` |
| `services/recommendation_engine.py` | 117 | 13 | 88.9% | `28, 35, 38, 70, 167-169, 17...` |
| `services/report_service.py` | 50 | 20 | 60.0% | `28, 39-42, 44-47, 50, 53, 6...` |
| `services/stationery_service.py` | 54 | 13 | 75.9% | `21, 32, 37, 40, 43, 63, 65,...` |
| `services/student_marks_service.py` | 155 | 15 | 90.3% | `77, 87, 110-111, 113-114, 1...` |
| `services/student_service.py` | 59 | 16 | 72.9% | `30, 36, 45-48, 50-51, 53, 6...` |
| `services/substitute_cpsat_solver.py` | 161 | 76 | 52.8% | `24, 31, 36, 63, 97, 106-109...` |
| `services/substitute_service.py` | 93 | 14 | 84.9% | `34, 92, 138, 143, 146, 149,...` |
| `services/tfidf_service.py` | 71 | 6 | 91.5% | `26, 46, 62, 79, 95, 122` |
| `services/time_service.py` | 76 | 29 | 61.8% | `30, 36, 44-46, 48-51, 53, 5...` |
| `services/web_portal_service.py` | 375 | 182 | 51.5% | `25, 256, 261-262, 271, 334,...` |
| `utils/__init__.py` | 5 | 0 | 100.0% | `` |
| `utils/exceptions.py` | 26 | 0 | 100.0% | `` |
| `utils/jwt_utils.py` | 131 | 19 | 85.5% | `33, 40, 42, 47, 52, 57, 69,...` |
| `utils/kiosk_token.py` | 57 | 10 | 82.5% | `25, 29, 33, 61, 67, 71, 77,...` |
| `utils/logger.py` | 28 | 3 | 89.3% | `13, 22, 56` |
| `utils/rate_limiter.py` | 34 | 5 | 85.3% | `25, 52-53, 56-57` |
| `utils/security.py` | 67 | 12 | 82.1% | `20, 25, 45, 77, 94, 102, 10...` |
