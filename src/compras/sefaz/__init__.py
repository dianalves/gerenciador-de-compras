"""Importação pela SEFAZ a partir do QR code da NFC-e.

Fluxo: QR code (foto ou link) -> navegador abre a consulta -> usuário resolve o
captcha (SP exige) -> HTML da nota -> parser -> NotaFiscal (valores exatos).
"""
