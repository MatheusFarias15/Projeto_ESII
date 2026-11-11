# Projeto_ESII — Nexus ERP

Aplicação Flask com cadastro, autenticação por senha com hash, sessão e bloqueio temporário após três tentativas inválidas (10 minutos), conforme a issue #4.

## Executar

```bash
export SECRET_KEY="uma-chave-aleatoria-longa"
export COOKIE_SECURE=0  # somente para desenvolvimento local em HTTP
python run.py
```

O banco SQLite padrão é `nexus_erp.db`. Para usar outro arquivo, defina `DATABASE_PATH`. Na inicialização, o sistema cria as tabelas necessárias e adiciona `password_hash` ao esquema antigo sem apagar usuários ou dados existentes. Hashes Werkzeug já armazenados na coluna antiga `password` são copiados para a nova coluna.

Em produção, configure uma `SECRET_KEY` estável e mantenha `COOKIE_SECURE=1` (padrão). Sem `SECRET_KEY`, a aplicação recusa iniciar, exceto em modo de teste ou debug. Os cookies são `HttpOnly`, `SameSite=Lax` e `Secure` por padrão. A aplicação também usa tokens CSRF em login, cadastro e logout e mantém um registro servidor de cada sessão autenticada para permitir revogação no logout.

Os testes automatizados estão em `tests/test_auth.py` e podem ser executados com `pytest`.
