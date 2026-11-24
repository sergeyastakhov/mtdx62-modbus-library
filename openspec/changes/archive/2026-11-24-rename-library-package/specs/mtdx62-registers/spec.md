# Spec Delta

## ADDED Requirements

### Requirement: Имя пакета и импортируемого модуля

Библиотека SHALL публиковаться на PyPI как `mtdx62-modbus-library` и импортироваться как
`mtdx62_modbus_library`. Других импортируемых имён дистрибутив MUST NOT предоставлять.

Имя модуля MUST отличаться от домена интеграции `mtdx62` и от каталога `custom_components/mtdx62`,
как требует `conventions/module-naming`.

#### Scenario: Установка и импорт

- **WHEN** пользователь выполняет `pip install mtdx62-modbus-library` и пишет
  `import mtdx62_modbus_library`
- **THEN** импорт проходит, и объект `Mtdx62Device` доступен из этого модуля

#### Scenario: Импорт рядом с компонентом интеграции

- **WHEN** импорт выполняется из каталога, где на пути лежит `custom_components/mtdx62`
- **THEN** импортируется библиотека, а не пакет интеграции

#### Scenario: Зависимость в манифесте интеграции

- **WHEN** интеграция объявляет зависимость
- **THEN** в `manifest.json` указано `mtdx62-modbus-library` с точной версией, а в коде
  импортируется `mtdx62_modbus_library`
