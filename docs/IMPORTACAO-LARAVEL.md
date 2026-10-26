# Importação dos dados do Laravel

## Antes de começar
1. Faça backup do banco de produção Laravel.
2. Trabalhe sobre uma cópia, nunca diretamente sobre o banco em uso.
3. O importador não importa usuários nem hashes de senha do Laravel. Crie usuários novos no MARKYS.
4. A aplicação usa IDs próprios; o importador preserva IDs livres quando possível e faz o mapeamento das relações de funcionário, tipo, crédito e histórico.

## Verificar a cópia SQLite
No Windows, com Python e dependências instalados, execute:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\import-laravel-sqlite.py --source "C:\\backup\\controle-folgas.sqlite" --dry-run
```

Se a validação listar as tabelas e quantidades esperadas, faça backup do banco de destino e execute sem `--dry-run`:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\import-laravel-sqlite.py --source "C:\\backup\\controle-folgas.sqlite"
```

O importador tenta importar tabelas de referência (`cbos`, `unidades`, `conselhos`, `estados`, `municipios`, `orgaos`, `contratos`, `setores`, `equipes`), funcionários, tipos de folga, créditos, histórico e limites por categoria. Registros que já existem não são sobrescritos. Conflitos de matrícula/CPF/e-mail, IDs ou datas duplicadas devem ser revisados no relatório.

## Observação importante sobre o ZIP fornecido
O arquivo `ubsdigital/database/database.sqlite` incluído no ZIP foi inspecionado apenas quanto ao esquema: ele contém tabelas de infraestrutura e usuários, mas **não contém** as tabelas `funcionarios`, `tipos_folgas`, `folgas` e `historico_folgas`. Portanto, ele não contém os registros operacionais necessários para migrar. O importador aborta sem alterar o destino se essas tabelas não existirem.

Se o Laravel usa MySQL/PostgreSQL ou se os dados estão em outro servidor, exporte uma cópia consistente para SQLite ou prepare uma exportação de dados compatível antes de importar. Não envie banco com dados pessoais para repositórios ou chats públicos.
