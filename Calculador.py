def Calificacion(quiz1, parcial1, nota1, nota2, nota3):
  P1 = quiz1 * 0.06
  P2 = parcial1 * 0.26
  P3 = ((nota1 + nota2 + nota3) / 3) * 0.48
  promedio_general = (quiz1 + parcial1 + ((nota1 + nota2 + nota3) / 3) / 3)
  nota_p = promedio_general * 0.20
  Nota_final = P1 + P2 + P3 + nota_p
  return Nota_final

quiz1 = float(input("ingrese la nota del quiz 1: "))
parcial1 = float(input("ingrese la nota del parcia 1: "))
nota1 = float(input("ingrese la nota 1 pos_asamblea: "))
nota2 = float(input("ingrese la nota 2 pos_asamblea: "))
nota3 = float(input("ingrese la nota 3 pos_asamblea: "))

print(f"la calificaciok es {Calificacion(quiz1, parcial1, nota1, nota2, nota3)}")