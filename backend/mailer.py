import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "nao-responda@lacc.edu.br")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

def is_smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

def send_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
    """
    Envia e-mail institucional via SMTP.
    Se o SMTP não estiver configurado, registra no log do servidor e permite fluxo de desenvolvimento.
    """
    if not is_smtp_configured():
        print(f"\n[MAILER DEV] ================================")
        print(f"[MAILER DEV] Para: {to_email}")
        print(f"[MAILER DEV] Assunto: {subject}")
        print(f"[MAILER DEV] Conteúdo de Texto:\n{text_content or html_content}")
        print(f"[MAILER DEV] ================================\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        
        print(f"[+] E-mail enviado com sucesso para {to_email}")
        return True
    except Exception as e:
        print(f"[-] Erro ao despachar e-mail via SMTP para {to_email}: {e}")
        return False

def send_verification_email(to_email: str, name: str, token: str, base_url: Optional[str] = None) -> bool:
    base = base_url or APP_BASE_URL
    verify_url = f"{base}/?verify_email={token}"
    subject = "Confirmação de E-mail — Liga Acadêmica de Ciências Criminais (LACC)"
    html = f"""
    <div style="font-family: Arial, sans-serif; background-color: #020817; color: #f8fafc; padding: 40px 20px;">
        <div style="max-width: 540px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #f59e0b; margin: 0; font-size: 22px;">LACC</h1>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Liga Acadêmica de Ciências Criminais</p>
            </div>
            <h2 style="color: #ffffff; font-size: 18px;">Olá, {name}!</h2>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Recebemos sua solicitação de cadastro na plataforma da LACC. Para confirmar a autenticidade do seu endereço de e-mail e dar continuidade à análise da sua candidatura pela diretoria, clique no botão abaixo:
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{verify_url}" style="background-color: #f59e0b; color: #020817; font-weight: bold; text-decoration: none; padding: 12px 28px; border-radius: 10px; display: inline-block; font-size: 14px;">
                    Confirmar Meu E-mail
                </a>
            </div>
            <p style="color: #64748b; font-size: 11px; line-height: 1.5;">
                Se você não realizou esta solicitação, por favor desconsidere esta mensagem.<br>
                Link alternativo: <a href="{verify_url}" style="color: #f59e0b;">{verify_url}</a>
            </p>
        </div>
    </div>
    """
    text = f"Olá, {name}!\nConfirme seu e-mail na LACC acessando: {verify_url}"
    return send_email(to_email, subject, html, text)

def send_password_reset_email(to_email: str, name: str, token: str, base_url: Optional[str] = None) -> bool:
    base = base_url or APP_BASE_URL
    reset_url = f"{base}/?reset_token={token}"
    subject = "Recuperação de Senha — LACC"
    html = f"""
    <div style="font-family: Arial, sans-serif; background-color: #020817; color: #f8fafc; padding: 40px 20px;">
        <div style="max-width: 540px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #f59e0b; margin: 0; font-size: 22px;">LACC</h1>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Recuperação Segura de Acesso</p>
            </div>
            <h2 style="color: #ffffff; font-size: 18px;">Prezado(a) {name},</h2>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Uma solicitação de redefinição de senha foi gerada para sua conta. Clique no botão abaixo para definir sua nova credencial de acesso:
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{reset_url}" style="background-color: #f59e0b; color: #020817; font-weight: bold; text-decoration: none; padding: 12px 28px; border-radius: 10px; display: inline-block; font-size: 14px;">
                    Redefinir Minha Senha
                </a>
            </div>
            <p style="color: #94a3b8; font-size: 12px;">
                Este link possui validade de 1 hora e só poderá ser utilizado uma única vez.
            </p>
            <p style="color: #64748b; font-size: 11px; line-height: 1.5; margin-top: 24px;">
                Se não solicitou esta redefinição, proteja sua conta e contate a administração.<br>
                Link alternativo: <a href="{reset_url}" style="color: #f59e0b;">{reset_url}</a>
            </p>
        </div>
    </div>
    """
    text = f"Olá, {name}!\nRedefina sua senha da LACC acessando: {reset_url}\nValidade: 1 hora."
    return send_email(to_email, subject, html, text)

def send_invite_email(to_email: str, name: str, token: str, base_url: Optional[str] = None) -> bool:
    base = base_url or APP_BASE_URL
    invite_url = f"{base}/?invite={token}"
    subject = "Convite Oficial de Admissão — Liga Acadêmica de Ciências Criminais"
    html = f"""
    <div style="font-family: Arial, sans-serif; background-color: #020817; color: #f8fafc; padding: 40px 20px;">
        <div style="max-width: 540px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #f59e0b; margin: 0; font-size: 22px;">LACC</h1>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Admissão Oficial de Membros</p>
            </div>
            <h2 style="color: #ffffff; font-size: 18px;">Parabéns, {name or 'Futuro Ligante'}!</h2>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Você foi oficialmente convidado(a) a ingressar no quadro de membros da <strong>Liga Acadêmica de Ciências Criminais (LACC)</strong>.
                Para ativar sua conta e acessar imediatamente a Área de Membros, clique no link abaixo:
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{invite_url}" style="background-color: #f59e0b; color: #020817; font-weight: bold; text-decoration: none; padding: 12px 28px; border-radius: 10px; display: inline-block; font-size: 14px;">
                    Aceitar Convite e Ativar Conta
                </a>
            </div>
            <p style="color: #94a3b8; font-size: 12px;">
                Este convite é individual, intransferível e expira em 7 dias.
            </p>
            <p style="color: #64748b; font-size: 11px; line-height: 1.5; margin-top: 24px;">
                Link direto: <a href="{invite_url}" style="color: #f59e0b;">{invite_url}</a>
            </p>
        </div>
    </div>
    """
    text = f"Olá, {name}!\nVocê foi convidado para a LACC. Ative sua conta em: {invite_url}\nValidade: 7 dias."
    return send_email(to_email, subject, html, text)

def send_approval_email(to_email: str, name: str, base_url: Optional[str] = None) -> bool:
    base = base_url or APP_BASE_URL
    login_url = f"{base}/"
    subject = "Sua Solicitação de Acesso foi Aprovada — Bem-vindo(a) à LACC!"
    html = f"""
    <div style="font-family: Arial, sans-serif; background-color: #020817; color: #f8fafc; padding: 40px 20px;">
        <div style="max-width: 540px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #10b981; margin: 0; font-size: 22px;">LACC</h1>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Homologação de Membro</p>
            </div>
            <h2 style="color: #ffffff; font-size: 18px;">Parabéns, {name}!</h2>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Sua solicitação de acesso à Área de Membros da LACC foi <strong>aprovada pela diretoria</strong>! Seu perfil agora está ativo no sistema acadêmico.
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{login_url}" style="background-color: #10b981; color: #020817; font-weight: bold; text-decoration: none; padding: 12px 28px; border-radius: 10px; display: inline-block; font-size: 14px;">
                    Acessar a Área de Membros
                </a>
            </div>
            <p style="color: #94a3b8; font-size: 12px;">
                Você já pode utilizar seu e-mail e senha cadastrados para entrar na plataforma.
            </p>
        </div>
    </div>
    """
    text = f"Parabéns, {name}!\nSua solicitação na LACC foi aprovada. Acesse: {login_url}"
    return send_email(to_email, subject, html, text)

def send_rejection_email(to_email: str, name: str, reason: Optional[str] = None) -> bool:
    subject = "Atualização sobre sua Solicitação de Acesso — LACC"
    reason_text = f"<p style='color: #cbd5e1; font-size: 13px;'><strong>Motivo:</strong> {reason}</p>" if reason else ""
    html = f"""
    <div style="font-family: Arial, sans-serif; background-color: #020817; color: #f8fafc; padding: 40px 20px;">
        <div style="max-width: 540px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #f59e0b; margin: 0; font-size: 22px;">LACC</h1>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Comissão de Admissão</p>
            </div>
            <h2 style="color: #ffffff; font-size: 18px;">Prezado(a) {name},</h2>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Agradecemos seu interesse em integrar a Liga Acadêmica de Ciências Criminais. Informamos que, neste momento, sua solicitação de acesso não pôde ser homologada.
            </p>
            {reason_text}
            <p style="color: #94a3b8; font-size: 12px; line-height: 1.5; margin-top: 20px;">
                Fique atento(a) aos próximos editais de processo seletivo e eventos abertos da Liga.
            </p>
        </div>
    </div>
    """
    text = f"Prezado(a) {name},\nSua solicitação de acesso na LACC não foi homologada neste momento.\nMotivo: {reason or 'Critérios regimentais de seleção.'}"
    return send_email(to_email, subject, html, text)

