CATEGORIAS = {
    "Despesa": {
        "Moradia": ["Aluguel", "Energia", "Água", "Internet", "Manutenção", "Condomínio"],
        "Alimentação": ["Supermercado", "Restaurante", "Ifood/Delivery", "Café/Lanche"],
        "Transporte": ["Combustível", "Uber/99", "Manutenção Veículo", "IPVA/Licenciamento", "Transporte Público"],
        "Lazer": ["Streaming", "Cinema/Teatro", "Viagem", "Bar/Balada", "Jogos"],
        "Educação": ["Faculdade", "Cursos Online", "Livros/Material", "Idiomas"],
        "Tecnologia": ["Hardware/Peças", "Software/Apps", "Nuvem/Servidores", "Eletrônicos"],
        "Saúde": ["Farmácia", "Consulta Médica", "Academia", "Terapia", "Plano de Saúde"],
        "Pessoal": ["Roupas", "Cosméticos", "Cabeleireiro", "Presentes"],
        "Financeiro": ["Taxas Bancárias", "Impostos", "Dívidas", "Pagamento de Fatura"],
        "Igreja": ["Dízimo", "Oferta", "Pacto", "Direcionado"],
    },
    "Receita": {
        "Trabalho Principal": ["Salário Líquido", "Adiantamento", "13º Salário", "Férias", "Bolsa de Estudos"],
        "Trabalho Extra": ["Freelance", "Consultoria", "Venda de Itens", "Cashback"],
        "Rendimentos": ["Dividendos", "Juros sobre Capital", "Aluguel de FIIs"],
    }
}

LISTA_CATEGORIAS_DESPESA = list(CATEGORIAS["Despesa"].keys())
LISTA_CATEGORIAS_RECEITA = list(CATEGORIAS["Receita"].keys())
LISTA_CATEGORIAS_INVESTIMENTO = [
    "Reserva de Emergência", 
    "Investimentos", 
    "Aposentadoria", 
    "Caixinha", 
    "Poupança",
    "Aportes"
]