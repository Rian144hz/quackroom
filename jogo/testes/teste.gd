## Base dos testes: herde desta classe e crie métodos que começam com "test_".
class_name Teste
extends RefCounted

var falhas: Array[String] = []


func igual(obtido: Variant, esperado: Variant, contexto := "") -> void:
	if obtido != esperado:
		falhas.append("%s esperado %s, veio %s" % [contexto, esperado, obtido])


func perto(obtido: Variant, esperado: Variant, contexto := "", tolerancia := 0.001) -> void:
	var diferenca: float
	if obtido is Vector3 or obtido is Vector2:
		diferenca = (obtido - esperado).length()
	else:
		diferenca = absf(obtido - esperado)
	if diferenca > tolerancia:
		falhas.append("%s esperado ~%s, veio %s" % [contexto, esperado, obtido])


func verdadeiro(condicao: bool, contexto := "") -> void:
	if not condicao:
		falhas.append("%s deveria ser verdadeiro" % contexto)
