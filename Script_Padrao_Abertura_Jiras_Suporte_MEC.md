# Script padrão para abertura de Jiras MEC

Use este modelo para padronizar chamados de suporte, reduzir retrabalho e facilitar a análise por Dados, Sistemas Web, Plataformas, Geração de Itens e Desenvolvimento Profissional.

## Descrição padrão para copiar no Jira

```text
[CONTEXTO]
Produto/Frente:
Ciclo/Ano:
Ambiente:
Perfil do usuário:
Login:
UF/Município/Escola/Turma/Aluno afetado:
Data e hora do ocorrido:

[PROBLEMA]
Resumo: Exemplo: a turma apresenta 15 estudantes, sendo que deveria conter 20.
Mensagem de erro exibida, se houver:
O problema é recorrente ou pontual?
Quantidade aproximada de usuários, escolas, turmas ou alunos afetados:

[PASSO A PASSO PARA REPRODUZIR]
1.
2.
3.
4.

[RESULTADO ESPERADO]
Descrever o comportamento correto esperado.

[RESULTADO ENCONTRADO]
Descrever o comportamento atual, incorreto ou divergente.

[EVIDÊNCIAS ANEXADAS]
- Print da tela inteira com URL visível:
- Print dos filtros aplicados:
- Print da mensagem de erro:
- Arquivo/exportação afetada, se houver:
- IDs técnicos: avaliação, escola, turma, aluno, usuário, card, arquivo ou registro:

[TRIAGEM DO SUPORTE]
Categoria provável:
Equipe indicada:
Prioridade sugerida:
Impacto operacional:
Observações adicionais:
```

## Modelo compacto para copiar no Jira

```text
Produto/Frente:
Ciclo/Ano:
Ambiente:
Perfil do usuário:
Login:
Entidade afetada: UF / município / escola / turma / aluno / usuário
Problema observado:
Passo a passo:
1.
2.
3.
Resultado esperado:
Resultado encontrado:
Evidências anexadas: Print tela inteira, URL, filtros, erro, arquivo/exportação, IDs
Impacto: Alto / Médio / Baixo + justificativa
Equipe indicada: Dados / Sistemas Web / Plataformas / Geração de Itens / Desenvolvimento Profissional / Suporte
```

## Evidências obrigatórias por tipo de problema

| Tipo de problema | Prints/evidências obrigatórias | IDs e dados técnicos mínimos |
|---|---|---|
| Resultados - consulta, publicação ou divergência | Tela do resultado, filtros aplicados, tela antes/depois, exportação e print da divergência. | Avaliação, ciclo, UF, município, escola, turma, aluno, card/resultado, data de atualização e perfil. |
| Aluno, turma ou escola não aparece | Tela da busca com filtro preenchido, tela da lista vazia e print do cadastro/base fonte quando disponível. | ID aluno, INEP escola, turma, etapa, município, UF, avaliação e ciclo. |
| Acesso, permissão ou perfil | Tela de login/perfil, menu ausente, mensagem de acesso negado e usuário logado visível sem senha. | E-mail/usuário, login, perfil esperado, perfil atual, sistema, ambiente e rota/menu. |
| Configuração de plataforma | Tela de configuração, campo alterado, regra selecionada e print antes/depois. | Avaliação, formulário, campo, regra, perfil, ambiente e versão/data da configuração. |
| Upload/download/arquivo | Tela do botão, erro no upload/download, nome/tamanho/tipo do arquivo e evidência de permissão. | Nome do arquivo, extensão, tamanho, horário, usuário, avaliação e link/registro relacionado. |
| Formulário, campo, grid ou select | Tela inteira, campo problemático, opções esperadas, opções exibidas e erro de validação. | Nome do formulário, campo, regra, perfil, avaliação, ambiente e dados usados no teste. |
| Dados, carga e validação | Comparação entre fonte e sistema, print de filtro, exportação e evidência da divergência. | Collection/tabela, identificador do registro, data da carga, regra de validação e origem do dado. |
| Instabilidade, performance ou tela não carrega | Print da tela, horário, URL, console/rede quando possível e vídeo curto. | Ambiente, navegador, usuário, horário, URL, endpoint afetado e frequência. |

## Checklist antes de encaminhar

- [ ] Resumo padronizado e objetivo.
- [ ] Produto, ciclo, ambiente, perfil e login preenchidos.
- [ ] Passo a passo reproduzível informado.
- [ ] Resultado esperado e resultado encontrado separados.
- [ ] Prints obrigatórios anexados conforme o tipo de problema.
- [ ] IDs técnicos informados quando houver aluno, escola, turma, avaliação, usuário, arquivo ou card.
- [ ] Impacto justificado com quantidade aproximada de afetados.
- [ ] Equipe indicada selecionada com base no tipo de problema.
- [ ] Prints sem senha, token ou dados sensíveis desnecessários.
