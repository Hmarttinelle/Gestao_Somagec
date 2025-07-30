# Ficheiro: stock/management/commands/run_backup.py

import os
import shutil
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage, get_connection

from stock.models import BackupConfig, Configuracao

class Command(BaseCommand):
    help = 'Executa o backup da base de dados e dos ficheiros de media, respeitando a frequência definida no admin.'

    def handle(self, *args, **options):
        self.stdout.write("--- Verificando a necessidade de executar o backup ---")
        
        config = BackupConfig.objects.first()
        if not config:
            self.stdout.write(self.style.WARNING("Configuração de backup não encontrada. A sair."))
            return

        # --- LÓGICA DE AGENDAMENTO ---
        run_backup = False
        now = timezone.now()

        if config.schedule == 'MANUAL':
            self.stdout.write("Backup configurado como 'Manual'. O comando não fará nada. Use a ação no admin.")
            return

        elif config.schedule == 'DIARIO':
            # Para backup diário, verificamos se o último foi há mais de 23 horas.
            if not config.last_backup_time or (now - config.last_backup_time) > timedelta(hours=23):
                run_backup = True
                self.stdout.write("Frequência 'Diário' detetada. Backup será executado.")
            else:
                self.stdout.write("Backup diário já foi executado recentemente. A saltar.")

        elif config.schedule == 'SEMANAL':
            # Para backup semanal, verificamos se o último foi há mais de 6 dias.
            if not config.last_backup_time or (now - config.last_backup_time) > timedelta(days=6):
                run_backup = True
                self.stdout.write("Frequência 'Semanal' detetada. Backup será executado.")
            else:
                self.stdout.write("Backup semanal já foi executado recentemente. A saltar.")

        if not run_backup:
            return # Termina a execução se não for para fazer o backup

        # --- SE CHEGÁMOS AQUI, O BACKUP SERÁ EXECUTADO ---
        self.stdout.write("\n--- Iniciando processo de backup via comando ---")
        temp_backup_dir = os.path.join(settings.BASE_DIR, 'temp_backup_dir_cmd')
        
        try:
            self.stdout.write("1. A carregar configurações de email...")
            if not config.recipient_email:
                raise CommandError("Email de destino para backups não configurado.")
            
            email_config = Configuracao.objects.first()
            if not email_config or not email_config.email_remetente or not email_config.password_remetente:
                 raise CommandError("Email de envio ou palavra-passe não configurados nas Configurações Gerais.")

            self.stdout.write("2. A preparar ficheiros locais para backup...")
            os.makedirs(temp_backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            # Backup da Base de Dados
            db_path = settings.DATABASES['default']['NAME']
            backup_db_name = f'db_backup_{timestamp}.sqlite3'
            backup_db_path = os.path.join(temp_backup_dir, backup_db_name)
            source_conn = sqlite3.connect(db_path)
            dest_conn = sqlite3.connect(backup_db_path)
            source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()
            self.stdout.write(f"   - Cópia da base de dados criada: {backup_db_name}")

            # Backup da Pasta Media
            media_root = settings.MEDIA_ROOT
            backup_media_name = f'media_backup_{timestamp}'
            zip_path = shutil.make_archive(os.path.join(temp_backup_dir, backup_media_name), 'zip', media_root)
            self.stdout.write(f"   - Ficheiro ZIP da pasta media criado: {backup_media_name}.zip")
            
            self.stdout.write(f"3. A enviar email para {config.recipient_email}...")
            subject = _("Backup Automático do Sistema Pedreira - {}").format(timestamp)
            body = _("Em anexo seguem os ficheiros de backup do sistema (base de dados e ficheiros de media).")
            
            email = EmailMessage(subject, body, email_config.email_remetente, [config.recipient_email])
            email.attach_file(backup_db_path)
            email.attach_file(zip_path)
            
            connection = get_connection(
                host=settings.EMAIL_HOST, port=settings.EMAIL_PORT,
                username=email_config.email_remetente, password=email_config.password_remetente,
                use_tls=settings.EMAIL_USE_TLS
            )
            connection.send_messages([email])
            
            config.last_backup_status = _("Sucesso via Comando")
            self.stdout.write(self.style.SUCCESS("\nBackup concluído e enviado com sucesso!"))

        except Exception as e:
            config.last_backup_status = _("Falhou via Comando: {}").format(str(e))
            self.stderr.write(self.style.ERROR(f"Ocorreu um erro durante o backup: {e}"))
        
        finally:
            config.last_backup_time = now
            config.save()
            if os.path.exists(temp_backup_dir):
                shutil.rmtree(temp_backup_dir)
            self.stdout.write("Limpeza de ficheiros temporários concluída.")