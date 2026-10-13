# Сводка 2-х час ГПН-Ямал — автоматическая сборка

Программа сама собирает «Сводку 2-х час ГПН-Ямал» из файла ПОНМ.

**Как это работает**

1. Вы кладёте файл ПОНМ (`.xlsb`, `.xlsm` или `.xlsx`) в папку `data/inbox` — или он приходит по почте.
2. Программа раз в минуту проверяет папку, находит новый или изменённый файл и собирает по нему сводку.
3. Готовая сводка появляется в папке `data/results`. Если включена отправка почты, она уходит письмом.

Всё остальное — журнал, старые файлы, повторные проверки — программа делает сама.

---

## 1. Что понадобится

- Сервер с Linux (инструкция ниже написана для Ubuntu / Debian) и права администратора на нём.
- Python 3.10 или новее (в Ubuntu 22.04 и новее он уже есть).
- *(необязательно)* LibreOffice — только если нужен PDF во вложении письма.
- *(необязательно)* Данные почтового сервера — если нужна отправка или приём писем.

---

## 2. Установка на сервер

Все команды выполняются на сервере. Папку проекта сначала скопируйте на сервер (например, через WinSCP или `scp`) — пусть она лежит в `~/svodka_upload`.

**Шаг 1. Установите нужные программы**

```bash
sudo apt update
sudo apt install -y python3 python3-venv
sudo apt install -y libreoffice-calc      # только если нужен PDF
```

**Шаг 2. Создайте отдельного пользователя для программы**

```bash
sudo useradd --system --home-dir /opt/svodka --shell /usr/sbin/nologin svodka
```

**Шаг 3. Разместите программу**

```bash
sudo mkdir -p /opt/svodka
sudo cp -r ~/svodka_upload/. /opt/svodka/
cd /opt/svodka
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
```

**Шаг 4. Создайте рабочие папки и выдайте права**

```bash
sudo mkdir -p data/inbox data/results data/errors data/state logs
sudo chown -R svodka:svodka data logs
sudo chmod 2770 data/inbox
sudo usermod -aG svodka ВАШ_ЛОГИН      # чтобы вы могли класть файлы в data/inbox
```

После этого выйдите с сервера и зайдите снова — права группы применятся.

**Шаг 5. Настройте программу** (подробности — в разделе 3)

```bash
sudo cp config/config.example.toml config/config.toml
sudo nano config/config.toml
sudo chown root:svodka config/config.toml
sudo chmod 640 config/config.toml
```

**Шаг 6. Проверьте настройки**

```bash
sudo -u svodka /opt/svodka/.venv/bin/python -m svodka check
```

Должно появиться «Настройки в порядке». Если есть ошибка — в тексте написано, что исправить.

**Шаг 7. Запустите как постоянную службу**

```bash
sudo cp deploy/svodka.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now svodka
sudo systemctl status svodka
```

В статусе должно быть `active (running)`. Служба сама запустится после перезагрузки сервера.

---

## 3. Настройка

Все настройки находятся в одном файле — **`config/config.toml`**. Каждая строка в нём подписана. Открывайте его любым текстовым редактором. После изменения перезапустите службу:

```bash
sudo systemctl restart svodka
```

### Главные параметры

| Параметр | Что означает | Значение по умолчанию |
|---|---|---|
| `inbox` | Папка, куда кладутся файлы ПОНМ | `data/inbox` |
| `results` | Папка с готовыми сводками | `data/results` |
| `interval_seconds` | Как часто проверять папку, секунд | `60` |
| `keep_days` | Через сколько дней удалять старые файлы (`0` — не удалять) | `30` |
| `timezone` | Часовой пояс, по которому определяется текущий день и время | `Asia/Yekaterinburg` |
| `max_file_mb` | Файлы больше этого размера не принимаются | `50` |

> **Важно про часовой пояс.** Сервер обычно работает по времени UTC. Сводка берёт данные за текущие часы по времени из параметра `timezone`, поэтому проверьте, что он указан верно.

### Приём файлов из почты

Включайте, если файлы ПОНМ приходят письмом в почтовый ящик, который хранится на этом же сервере в формате mbox.

```toml
[mail_in]
enabled          = true
mbox_path        = "/путь/к/почтовому/ящику"
restrict_senders = true
allowed_senders  = ["ivanov@company.ru", "@company.ru"]
```

- `restrict_senders` — `true` (по умолчанию): вложения принимаются только от отправителей из `allowed_senders`. `false`: проверка отключена, вложения принимаются от любых отправителей, а `allowed_senders` можно не заполнять.
- `allowed_senders` — **обязательный** список при `restrict_senders = true`. Можно писать адрес целиком или весь домен (`@company.ru`). Письма от остальных игнорируются.
- Если ящик лежит в папке `/home/...`, откройте `deploy/svodka.service` и замените `ProtectHome=true` на `ProtectHome=read-only`.

Если почта хранится не на сервере — просто кладите файлы в `data/inbox` сами.

### Отправка готовой сводки по почте

```toml
[mail_out]
enabled         = true
from            = "svodka@company.ru"
to              = ["boss@company.ru", "team@company.ru"]
reply_to_sender = false
attach_pdf      = true

[smtp]
server   = "mail.company.ru"
port     = 587
security = "starttls"
login    = "svodka@company.ru"
```

- `reply_to_sender = true` — копия уходит ещё и тому, кто прислал файл ПОНМ по почте.
- `attach_pdf = true` — к письму прикладывается PDF (нужен LibreOffice).
- Если письмо получается слишком большим (`max_attachment_mb`), вложения не прикладываются, а в тексте письма сказано, где лежит файл.

**Пароль от почты не пишите в `config.toml`.** Сохраните его так:

```bash
sudo mkdir -p /etc/svodka
sudo nano /etc/svodka/svodka.env
```

В открывшемся файле одна строка:

```
SVODKA_SMTP_PASSWORD=ваш_пароль
```

Затем закройте доступ к файлу и перезапустите службу:

```bash
sudo chmod 600 /etc/svodka/svodka.env
sudo systemctl restart svodka
```

---

## 4. Ежедневная работа

**Положить файл вручную.** Скопируйте файл ПОНМ в папку `/opt/svodka/data/inbox` (например, через WinSCP). Через минуту готовая сводка будет в `/opt/svodka/data/results` под именем:

```
Сводка 2-х час ГПН-Ямал — <имя вашего файла>.xlsx
```

**Получить по почте.** Если включены приём и отправка — ничего делать не нужно: пришёл файл — ушла сводка.

**Обновили файл ПОНМ.** Положите новую версию в ту же папку — сводка пересоберётся.

**Посмотреть, что происходит:**

```bash
tail -n 50 /opt/svodka/logs/svodka.log        # последние записи журнала
sudo systemctl status svodka                  # работает ли служба
```

**Остановить / запустить / перезапустить:**

```bash
sudo systemctl stop svodka
sudo systemctl start svodka
sudo systemctl restart svodka
```

**Собрать сводку один раз вручную:**

```bash
cd /opt/svodka
sudo -u svodka .venv/bin/python -m svodka build "data/inbox/Мой файл.xlsb"
```

---

## 5. Если что-то не работает

| Что происходит | Что делать |
|---|---|
| Сводка не появляется | Проверьте, что файл лежит именно в `data/inbox` и имеет расширение `.xlsb`, `.xlsm` или `.xlsx`. Посмотрите журнал `logs/svodka.log`. |
| Файл исчез из `data/inbox` и оказался в `data/errors` | Файл не похож на ПОНМ, слишком большой или повреждён. Причина записана в журнале. |
| Письмо не приходит | В журнале найдите строку «письмо не отправлено» — рядом причина. Проверьте `server`, `port`, `login` и пароль. |
| В журнале «Message size exceeds» | Почтовый сервер не принимает такие большие письма. Уменьшите `max_attachment_mb` или поставьте `attach_pdf = false`. |
| Файлы из почты не принимаются | В журнале строка «не из списка разрешённых отправителей». Добавьте адрес в `allowed_senders` или отключите проверку: `restrict_senders = false`. |
| Данные за текущий день неполные или сдвинуты по времени | Проверьте `timezone` в `config/config.toml`. |
| Служба не запускается | Выполните `python -m svodka check` (шаг 6) — программа назовёт, что не так в настройках. |
| Написано «не найден лист-образец» / «не найден файл-образец» | Проверьте, что файл `templates/svodka_template.xlsx` на месте. |

---

## 6. Безопасность

**Что уже сделано в программе:**

- По умолчанию принимаются файлы только от отправителей из списка `allowed_senders`. Без списка приём почты не включится, если не отключить проверку (`restrict_senders = false`) — делать это стоит только для закрытого ящика. Особенно осторожно сочетать это с `reply_to_sender = true`: готовая сводка уйдёт любому, кто прислал файл.
- Имена вложений очищаются — файл не может попасть в чужую папку. Принимаются только `.xlsb`, `.xlsm`, `.xlsx`.
- Файлы проверяются по размеру и на «раздутое» содержимое; подозрительные уходят в `data/errors`.
- Текст из присланных файлов не может превратиться в формулу в готовой сводке.
- Почта отправляется только по защищённому соединению. Если указан логин с паролем, а соединение незащищённое, программа не запустится.
- Пароль хранится отдельно от настроек, в файле, закрытом от других пользователей.
- Программа не открывает никаких сетевых портов и не принимает подключений извне.
- Служба работает от отдельного пользователя без прав администратора и видит только свои папки.
- Все настройки проверяются при запуске; опечатка в названии параметра не пропускается молча.

**Что нужно сделать вам как владельцу сервера:**

- Вход на сервер — только по ключу SSH, вход по паролю отключить.
- Включить файрвол: открыт только порт SSH.
- Включить автоматические обновления безопасности (`sudo apt install unattended-upgrades`).
- Не копировать `config/config.toml` и `/etc/svodka/svodka.env` в общие папки, почту и репозитории.
- Раз в несколько месяцев менять пароль от почты и обновлять список `allowed_senders`.

---

## 7. Обновление программы

```bash
sudo systemctl stop svodka
sudo cp -r ~/новая_версия/svodka ~/новая_версия/deploy ~/новая_версия/requirements.txt /opt/svodka/
sudo /opt/svodka/.venv/bin/pip install -r /opt/svodka/requirements.txt
sudo systemctl start svodka
```

Файл настроек и рабочие папки при этом не затрагиваются.

---

## 8. Запуск на Windows (для проверки)

1. Установите Python с сайта python.org (отметьте «Add Python to PATH»).
2. В папке проекта откройте PowerShell и выполните:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy config\config.example.toml config\config.toml
.venv\Scripts\python -m svodka check
.venv\Scripts\python -m svodka watch
```

Положите файл в `data\inbox` — сводка появится в `data\results`. Остановка — `Ctrl+C`.

---

## 9. Что где лежит

```
svodka/
├── config/
│   ├── config.example.toml   образец настроек
│   └── config.toml           ваши настройки (создаёте вы)
├── data/
│   ├── inbox/                сюда кладут файлы ПОНМ
│   ├── results/              готовые сводки
│   ├── errors/               файлы, которые не удалось принять
│   └── state/                служебные записи программы
├── logs/svodka.log           журнал работы
├── templates/                образец сводки (не менять)
├── deploy/svodka.service     файл для запуска службы
├── svodka/                   программа
├── tests/                    автоматические проверки
├── tools/                    вспомогательные инструменты
└── requirements.txt          список необходимых библиотек
```
