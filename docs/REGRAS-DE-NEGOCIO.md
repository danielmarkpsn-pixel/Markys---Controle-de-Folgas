# MARKYS — regras de negócio e mapeamento do projeto de exemplo

Fonte: ZIP Laravel enviado pelo usuário, principalmente `FolgaController.php`, `FuncionarioController.php`, `HistoricoFolgaController.php`, modelos e migrações de funcionários, tipos, créditos, histórico, limites e tabelas organizacionais. O projeto Laravel original permanece inalterado.

## Regras reproduzidas
1. Um crédito de folga pertence a um funcionário e tipo; registra descrição, data do evento, quantidade total e saldo disponível.
2. A data limite é data do evento + `dias_validade`; o gozo é permitido até o último dia, inclusive.
3. Registrar gozo reduz o saldo; cancelar um gozo devolve o saldo e registra auditoria.
4. Um funcionário não pode ter dois registros de gozo na mesma data, mesmo em turnos ou créditos diferentes.
5. O limite diário é contado por categoria CBO e data, conforme o comportamento observado no controller original.
6. O histórico guarda data da solicitação, data de gozo, quantidade, turno, funcionário, crédito de origem e usuário que registrou.
7. Funcionário com `data_saida` é tratado como inativo para novos créditos/agendamentos.
8. Créditos disponíveis e expirados são distinguidos pela data de validade.
9. O histórico pode ser filtrado por mês/ano e categoria e exportado para CSV.
10. Operações administrativas são protegidas pelo perfil admin; perfil consulta pode visualizar sem alterar.

## Campos do funcionário mapeados
A versão independente agora inclui os campos identificados na migração Laravel: nome, data de nascimento, sexo, pai/mãe, DDD/telefone, estado civil, nacionalidade, naturalidade, matrícula, CNS, CBO/categoria, conselho e registro de classe, UF de registro, unidade CNES, equipe INE, contrato, nomeação, posse, entrada/saída e motivo, setor, turno, carga horária, endereço, e-mail, CPF, NIS, RG/órgão/UF/data, CTPS, título eleitoral e caminho da imagem.

Os campos são opcionais para permitir a migração gradual; a tela de listagem não expõe CPF, CNS, endereço ou documentos. A rota de detalhes de funcionário e a edição exigem perfil admin. A categoria pode ser derivada do CBO quando a tabela de referência está preenchida; o código também é guardado para importação.

## Segurança e arquitetura
- FastAPI + SQLAlchemy; SQLite para desenvolvimento local; PostgreSQL obrigatório em produção.
- Senhas novas são armazenadas com scrypt; sessão assinada; limite de tentativas de login por endereço de origem.
- O modo produção exige chave persistente forte, PostgreSQL e cookies seguros.
- O backend permanece em `127.0.0.1:8000`; o acesso LAN deve passar por HTTPS (Caddy) e firewall limitado à sub-rede autorizada.
- Backups usam a API de cópia consistente do SQLite ou `pg_dump` no PostgreSQL.
- Importação não migra usuários nem senhas do Laravel; são criadas contas novas.

## Pontos que exigem validação funcional
- O controller original atualiza um crédito substituindo o saldo pela quantidade total; a versão independente não oferece ainda edição destrutiva de crédito.
- Confirmar se o limite é contado como número de solicitações, independentemente de turno, e se existem exceções.
- Confirmar o prazo padrão dos tipos de folga. A interface exige preenchimento explícito.
- Revisar todos os registros após importação, especialmente créditos parciais, datas, saldo e limites.
