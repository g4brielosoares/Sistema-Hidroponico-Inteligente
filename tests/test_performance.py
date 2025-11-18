import time

from backend.services.xml_service import XMLService


def test_simulacao_performance():
    """
    Teste acadêmico de desempenho (RNF1):
    roda 100 ciclos de simulação e espera que termine em < 2 segundos.
    Isso significa que, para um conjunto pequeno de sensores, o sistema
    consegue processar ~100 leituras/s com validação via XSD.
    """
    service = XMLService()

    start = time.perf_counter()
    num_ciclos = 100

    for _ in range(num_ciclos):
        service.simular_ciclo()

    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"Simulação demorou {elapsed:.3f}s (esperado < 2s)"
