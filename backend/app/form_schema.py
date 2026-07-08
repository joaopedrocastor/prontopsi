"""Definicao canonica da Ficha de Anamnese (fonte unica de verdade).

O mesmo esquema alimenta:
  - a renderizacao do formulario na interface (via API /api/form-schema);
  - a geracao do PDF (mesma ordem e rotulos da ficha em papel);
  - a deteccao de campos vazios (aviso de preenchimento incompleto).

Versionado por FORM_VERSION: fichas antigas guardam a versao com que foram
criadas e continuam abrindo mesmo se o formulario evoluir.

Tipos de campo:
  text      - linha unica
  textarea  - texto longo (rows = altura sugerida)
  date      - data ISO
  age       - idade calculada (derivada de `source`, somente leitura)
  radio     - escolha unica (options)
  select    - escolha unica em lista (options)
  checkboxes- multipla escolha (options); valor = lista de rotulos

Larguras (width): "full" | "half" | "third".
count_missing=False -> campo nao entra na contagem de "campos vazios".
"""
from __future__ import annotations

FORM_VERSION = "1"

SIM_NAO = ["Sim", "Não"]


def _f(key, label, type="text", width="full", **extra):
    field = {"key": key, "label": label, "type": type, "width": width}
    field.update(extra)
    return field


SECTIONS = [
    {
        "id": "identificacao_pessoal",
        "title": "IDENTIFICAÇÃO PESSOAL",
        "fields": [
            _f("nome", "Nome", width="full"),
            _f("data_primeiro_atendimento", "Data do primeiro atendimento", "date", "half"),
            _f("data_nascimento", "Data de nascimento", "date", "half"),
            _f("idade", "Idade", "age", "half", source="data_nascimento", count_missing=False),
            _f("sexo", "Sexo", "radio", "half", options=["F", "M"]),
            _f("naturalidade", "Naturalidade", width="half"),
            _f("religiao", "Religião", width="half"),
            _f("escolaridade", "Escolaridade", width="full"),
            _f("endereco", "Endereço atual", "textarea", "full", rows=2),
            _f("cep", "CEP", width="third"),
            _f("cidade", "Cidade", width="third"),
            _f("uf", "UF", width="third"),
            _f("telefones", "Telefones de contato", width="full"),
        ],
    },
    {
        "id": "identificacao_pais",
        "title": "IDENTIFICAÇÃO DOS PAIS",
        "fields": [
            _f("pai_nome", "Pai", width="full"),
            _f("pai_profissao", "Profissão", width="half"),
            _f("pai_idade", "Idade", width="half"),
            _f("mae_nome", "Mãe", width="full"),
            _f("mae_profissao", "Profissão", width="half"),
            _f("mae_idade", "Idade", width="half"),
            _f("cuidador_nome", "Cuidador(a)", width="half"),
            _f("cuidador_vinculo", "Vínculo", width="half"),
            _f("cuidador_profissao", "Profissão", width="half"),
            _f("cuidador_idade", "Idade", width="half"),
            _f("pais_telefones", "Telefones", width="full"),
        ],
    },
    {
        "id": "entrevistado",
        "title": "ENTREVISTADO",
        "fields": [
            _f("entrevistado_nome", "Nome", width="full"),
            _f("entrevistado_vinculo", "Vínculo", width="half"),
            _f("entrevistado_telefone", "Telefone", width="half"),
        ],
    },
    {
        "id": "solicitante",
        "title": "PRINCIPAL SOLICITANTE DO CONTATO",
        "fields": [
            _f("solicitante", "Solicitante", "checkboxes", "full",
               options=["Familiares", "Escola", "Médico", "Outros"]),
            _f("medico_especialidade", "Especialidade (se Médico)", width="half", count_missing=False),
            _f("outros_especificar", "Especificar (se Outros)", width="half", count_missing=False),
            _f("queixa_principal", "Queixa principal", "textarea", "full", rows=6),
            _f("historico_queixa", "Histórico da queixa", "textarea", "full", rows=6),
            _f("acompanhamento_saude", "Paciente está em acompanhamento de saúde?", "radio", "half",
               options=SIM_NAO),
            _f("acompanhamento_qual", "Qual/Quais?", width="half", count_missing=False),
            _f("farmacos", "Fármacos em uso", "textarea", "full", rows=3),
            _f("alergia_medicamento", "Alergia a algum medicamento", width="full"),
        ],
    },
    {
        "id": "gestacao",
        "title": "CONCEPÇÃO, GESTAÇÃO E PARTO",
        "fields": [
            _f("concepcao", "Informações gerais acerca da concepção", "textarea", "full", rows=4,
               hint="idade da mãe quando engravidou, gravidez planejada ou não, reação do pai, "
                    "reação dos familiares, etc."),
            _f("gestacao", "Informações gerais sobre a gestação", "textarea", "full", rows=5,
               hint="fez pré-natal, doenças, quedas, exposição a Raio X, uso de medicamentos, "
                    "uso de drogas, tentativas de aborto, etc."),
            _f("parto", "Informações sobre o parto", "textarea", "full", rows=3),
            _f("chorou_ao_nascer", "Chorou ao nascer?", width="third"),
            _f("ficou_incubadora", "Ficou em incubadora?", width="third"),
            _f("incubadora_tempo", "Tempo", width="third", count_missing=False),
            _f("complicacoes_parto", "Complicações após o parto", "textarea", "full", rows=3),
        ],
    },
    {
        "id": "desenvolvimento",
        "title": "DESENVOLVIMENTO",
        "fields": [
            _f("equilibrio_pescoco", "Quando se deu o equilíbrio do pescoço? Demorou?", width="full"),
            _f("sentou", "Com que idade sentou? Demorou?", width="full"),
            _f("andou", "Andou com que idade? Demorou?", width="full"),
            _f("falou", "Com que idade falou? Demorou?", width="full"),
            _f("trocou_letras", "Trocou letras?", width="half"),
            _f("gaguejou", "Gaguejou?", width="half"),
            _f("sob_cuidados", "A criança ficou sob cuidados de quem", "textarea", "full", rows=2,
               hint="familiares, babá, creche, etc."),
            _f("doencas_internacoes", "Histórico de doenças e internações", "textarea", "full", rows=3),
        ],
    },
    {
        "id": "relacionamento_familiar",
        "title": "RELACIONAMENTO FAMILIAR",
        "fields": [
            _f("mora_com", "A criança mora com quem?", width="full"),
            _f("pais_moram_juntos", "Os pais moram juntos?", width="full"),
            _f("relacionamento_pais", "Relacionamento dos pais", width="full"),
            _f("relacao_crianca_pais", "Como a criança se relaciona com os pais", "textarea", "full", rows=2),
            _f("relacao_irmaos", "Se tiver irmãos, como é o relacionamento com eles", "textarea", "full", rows=2),
            _f("outros_familiares_educacao", "Outros familiares que interferem na educação da criança",
               "textarea", "full", rows=2),
        ],
    },
    {
        "id": "antecedentes",
        "title": "ANTECEDENTES FAMILIARES",
        "fields": [
            _f("doenca_mental_familia", "História de doença mental / transtornos psiquiátricos na família",
               "textarea", "full", rows=3),
        ],
    },
    {
        "id": "vida_academica",
        "title": "VIDA ACADÊMICA",
        "fields": [
            _f("vai_escola", "Vai à escola?", "radio", "half", options=SIM_NAO),
            _f("tipo_escola", "Tipo de escola", "radio", "half",
               options=["Pública", "Particular", "Conveniada"]),
            _f("serie", "Cursa qual série?", width="half"),
            _f("repetiu_serie", "Já repetiu alguma série?", width="half"),
            _f("quantas_vezes", "Quantas vezes?", width="half", count_missing=False),
            _f("relacionamento_colegas", "Relacionamento com os colegas", "textarea", "full", rows=2),
            _f("relacionamento_professores", "Relacionamento com os professores (atuais e passados)",
               "textarea", "full", rows=2),
            _f("habilidades_deficits", "Habilidades e déficits acadêmicos", "textarea", "full", rows=2,
               hint="cálculo, leitura, artes, etc."),
            _f("gosta_escola", "Gosta de ir pra escola?", width="full"),
            _f("professores_falam",
               "O que os professores falam sobre seu comportamento e desempenho acadêmico?",
               "textarea", "full", rows=3),
            _f("habilidades_nao_academicas", "Habilidades não acadêmicas", "textarea", "full", rows=3,
               hint="esportes, bicicleta, vídeo-game, tarefas domésticas, música, "
                    "aparelhos eletrônicos, etc."),
        ],
    },
    {
        "id": "sono",
        "title": "SONO",
        "fields": [
            _f("sono", "Informações sobre o sono", "textarea", "full", rows=8,
               hint="dorme quantas horas por noite, que horas costuma dormir e acordar, dorme "
                    "durante o dia, fala dormindo, tem pesadelos, sudorese, dorme sozinho, com "
                    "irmãos ou com os pais, etc."),
        ],
    },
    {
        "id": "lazer",
        "title": "LAZER",
        "fields": [
            _f("brinquedos_prediletos", "Brinquedos prediletos", "textarea", "full", rows=2),
            _f("brincadeiras_preferidas", "Brincadeiras preferidas", "textarea", "full", rows=2),
            _f("sozinho_ou_amigos", "Prefere brincar sozinho ou com amigos?", width="full"),
            _f("outras_atividades_lazer", "Outras atividades de lazer", "textarea", "full", rows=2),
        ],
    },
    {
        "id": "relacionamento_interpessoal",
        "title": "RELACIONAMENTO INTERPESSOAL",
        "fields": [
            _f("tem_amigos", "Tem amigos?", width="full"),
            _f("habilidades_sociais", "Habilidades sociais", "textarea", "full", rows=5,
               hint="habilidade para fazer amigos; é briguento, colaborativo, querido ou os amigos "
                    "o evitam; expressa sentimentos; solicita e oferece ajuda; etc."),
            _f("atividade_fisica", "Pratica atividade física?", "radio", "half", options=SIM_NAO),
            _f("atividade_fisica_qual", "Qual?", width="half", count_missing=False),
            _f("atividade_fisica_frequencia", "Frequência", width="full", count_missing=False),
        ],
    },
    {
        "id": "outras_informacoes",
        "title": "OUTRAS INFORMAÇÕES IMPORTANTES",
        "fields": [
            _f("outras_informacoes", "Outras informações importantes", "textarea", "full", rows=10),
            _f("responsavel_entrevista", "Responsável pela entrevista", width="full"),
        ],
    },
]


def get_schema() -> dict:
    return {"form_version": FORM_VERSION, "sections": SECTIONS}


def iter_fields():
    """Itera (secao, campo) em ordem."""
    for section in SECTIONS:
        for field in section["fields"]:
            yield section, field


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def missing_report(data: dict | None) -> dict:
    """Relatorio de campos vazios para o aviso nao bloqueante.

    Retorna {total, sections:[{id,title,missing:[labels]}]}.
    """
    data = data or {}
    sections_out = []
    total = 0
    for section in SECTIONS:
        missing = []
        for field in section["fields"]:
            if not field.get("count_missing", True):
                continue
            if _is_empty(data.get(field["key"])):
                missing.append(field["label"])
        if missing:
            total += len(missing)
            sections_out.append(
                {"id": section["id"], "title": section["title"], "missing": missing}
            )
    return {"total": total, "sections": sections_out}
