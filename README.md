# detective-plants
| Проект | Сервис | БД | Порт | Таблицы |
|---|---|---|---|---|
| auth-service/ | Auth Service | `auth_db` | 5431 | roles, users, profiles, referral_profiles, user_settings |
| request-service/ | Request Service | `request_db` | 5542 | requests, request_photos, diseases |
| expert-service/ | Expert Service | `expert_db` | 5433 | expert_responses, diagnoses, treatment_checklists, ml_training_examples |
| recovery-service/ | Recovery Service | `recovery_db` | 5434 | recovery_trackers, treatment_history |
| chat-service/ | Chat Service | `chat_db` | 5435 | chat_rooms, messages, video_rooms, moderation_rules, moderation_logs |
| payment-service/ | Payment Service | `payment_db` | 5436 | transactions, withdrawals |
| notification-service/ | Notification Service | `notification_db` | 5437 | notifications |
| analytics-service/ | Analytics Service | `analytics_db` | 5438 | expert_stats, disease_stats |
| admin-service/ | Admin Service | `admin_db` | 5439 | expert_applications |
| satellite-service/ | Satellite Service | `satellite_db` | 5440 | fields, ndvi_measurements, satellite_alerts |
