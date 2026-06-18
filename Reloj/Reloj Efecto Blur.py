import os
import tkinter as tk
from datetime import datetime
from abc import ABC, abstractmethod
from PIL import Image, ImageFilter, ImageTk

class ServicioTiempo(ABC):
    @abstractmethod
    def obtener_datos_actuales(self) -> dict:
        pass

class RelojServicioTiempo(ServicioTiempo):
    def obtener_datos_actuales(self) -> dict:
        ahora = datetime.now()
        return {
            "hora_minuto": ahora.strftime("%H:%M"),
            "segundos": ahora.strftime("%S"),
            "fecha": ahora.strftime("%b %d, %Y").upper(),
            "hora_pura": ahora.hour,
            "segundo_puro": ahora.second
        }

class EvaluadorPeriodo:
    def __init__(self):
        self._periodos = [
            (6, "NIGHT"),
            (12, "MORNING"),
            (18, "AFTERNOON"),
            (24, "EVENING")
        ]

    def determinar_bloque(self, hora: int) -> str:
        if not (0 <= hora < 24):
            return "UNKNOWN"
            
        for limite, etiqueta in self._periodos:
            if hora < limite:
                return etiqueta
        return "UNKNOWN"

class MotorRenderBlur:
    @staticmethod
    def generar_fondo(ventana_padre: tk.Tk, ancho: int, alto: int, ruta_salida: str) -> ImageTk.PhotoImage:
        # Creamos una imagen base completamente oscura usando Pillow
        img = Image.new("RGB", (ancho, alto), "#050508")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Dibujamos las formas de color directamente en la imagen antes del blur
        draw.ellipse([ancho * 0.1, alto * 0.1, ancho * 0.6, alto * 0.6], fill="#7000ff")
        draw.ellipse([ancho * 0.4, alto * 0.4, ancho * 0.85, alto * 0.85], fill="#00f2fe")
        
        # Aplicamos el filtro de desenfoque gaussiano de forma nativa
        img_difuminada = img.filter(ImageFilter.GaussianBlur(radius=55))
        
        # Convertimos la imagen procesada a un formato que Tkinter entienda
        resultado = ImageTk.PhotoImage(img_difuminada)
        return resultado

class VistaRelojMinimalista:
    def __init__(self, ventana: tk.Tk, servicio_tiempo: ServicioTiempo, evaluador: EvaluadorPeriodo):
        self._ventana = ventana
        self._servicio_tiempo = servicio_tiempo
        self._evaluador = evaluador
        self._archivo_temporal = "ctx_cache_bg.ps"
        
        self._configurar_ventana()
        self._inicializar_componentes()
        self._bucle_renderizado()

    def _configurar_ventana(self):
        self._ventana.title("Chronos Minimal")
        self._ventana.geometry("400x400")
        self._ventana.resizable(False, False)
        self._ventana.configure(bg="#050508")

    def _inicializar_componentes(self):
        self._lienzo = tk.Canvas(self._ventana, width=400, height=400, bg="#050508", highlightthickness=0)
        self._lienzo.pack(fill="both", expand=True)
        
        try:
            self._fondo_blur = MotorRenderBlur.generar_fondo(self._ventana, 400, 400, self._archivo_temporal)
            self._lienzo.create_image(0, 0, image=self._fondo_blur, anchor="nw")
        except Exception:
            pass

        self._lienzo.create_rectangle(50, 130, 350, 270, fill="#0b0c10", outline="#1f2430", width=1)

        # Se eliminó "light" para evitar el crash de Tcl/Tk en entornos Windows
        self._lbl_hora = self._lienzo.create_text(
            195, 185, text="00:00", font=("Arial", 52, "bold"), fill="#ffffff"
        )
        self._lbl_segundos = self._lienzo.create_text(
            305, 195, text="00", font=("Arial", 16, "bold"), fill="#00f2fe"
        )
        self._lbl_fecha = self._lienzo.create_text(
            200, 235, text="DATE", font=("Arial", 11), fill="#525866"
        )

    def _bucle_renderizado(self):
        datos = self._servicio_tiempo.obtener_datos_actuales()
        periodo = self._evaluador.determinar_bloque(datos["hora_pura"])
        
        meta_fecha = f"{datos['fecha']}  •  {periodo}"
        color_pulso = "#ffffff" if datos["segundo_puro"] % 2 == 0 else "#a4a9b8"
        
        self._lienzo.itemconfig(self._lbl_hora, text=datos["hora_minuto"], fill=color_pulso)
        self._lienzo.itemconfig(self._lbl_segundos, text=datos["segundos"])
        self._lienzo.itemconfig(self._lbl_fecha, text=meta_fecha)
        
        self._ventana.after(1000, self._bucle_renderizado)

if __name__ == "__main__":
    root = tk.Tk()
    
    servicio = RelojServicioTiempo()
    analizador_periodo = EvaluadorPeriodo()
    
    app = VistaRelojMinimalista(root, servicio, analizador_periodo)
    root.mainloop()