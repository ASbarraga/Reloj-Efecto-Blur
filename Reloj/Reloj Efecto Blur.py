import os
import tkinter as tk
from datetime import datetime
from abc import ABC, abstractmethod
from PIL import Image, ImageFilter, ImageTk
import urllib.request
import json
import threading

WEATHER_DESC = {
    0: ("☀️", "Despejado"),
    1: ("🌤️", "Parcialmente Nublado"),
    2: ("🌤️", "Parcialmente Nublado"),
    3: ("☁️", "Nublado"),
    45: ("🌫️", "Niebla"),
    48: ("🌫️", "Niebla"),
    51: ("🌧️", "Llovizna"),
    53: ("🌧️", "Llovizna"),
    55: ("🌧️", "Llovizna"),
    56: ("🌧️", "Llovizna Helada"),
    57: ("🌧️", "Llovizna Helada"),
    61: ("🌧️", "Lluvia"),
    63: ("🌧️", "Lluvia"),
    65: ("🌧️", "Lluvia Fuerte"),
    66: ("🌧️", "Lluvia Helada"),
    67: ("🌧️", "Lluvia Helada"),
    71: ("❄️", "Nieve"),
    73: ("❄️", "Nieve"),
    75: ("❄️", "Nieve Fuerte"),
    77: ("❄️", "Granizo de Nieve"),
    80: ("🌧️", "Chubascos"),
    81: ("🌧️", "Chubascos"),
    82: ("🌧️", "Chubascos Fuertes"),
    85: ("❄️", "Chubascos Nieve"),
    86: ("❄️", "Chubascos Nieve"),
    95: ("⛈️", "Tormenta"),
    96: ("⛈️", "Tormenta con Granizo"),
    99: ("⛈️", "Tormenta con Granizo"),
}

MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

class GestorClima:
    def __init__(self):
        self.ciudad = "Cargando..."
        self.pais = ""
        self.temperatura = "--"
        self.icono = "⏳"
        self.descripcion = "Obteniendo clima..."
        self.actualizado = False

    def actualizar_datos(self, callback_actualizar_ui=None):
        def tarea():
            try:
                with urllib.request.urlopen("http://ip-api.com/json/", timeout=4) as response:
                    loc_data = json.loads(response.read().decode())
                    self.ciudad = loc_data.get("city", "Lima")
                    self.pais = loc_data.get("countryCode", "PE")
                    lat = loc_data.get("lat", -12.04637)
                    lon = loc_data.get("lon", -77.042793)
                
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                with urllib.request.urlopen(weather_url, timeout=4) as w_response:
                    w_data = json.loads(w_response.read().decode())
                    current = w_data.get("current_weather", {})
                    temp = current.get("temperature", 18.0)
                    code = current.get("weathercode", 0)
                    
                    self.temperatura = f"{round(temp)}°C"
                    icono, desc = WEATHER_DESC.get(code, ("☀️", "Despejado"))
                    self.icono = icono
                    self.descripcion = desc
                    self.actualizado = True
            except Exception:
                self.ciudad = "Lima"
                self.pais = "PE"
                self.temperatura = "18°C"
                self.icono = "☀️"
                self.descripcion = "Despejado"
                self.actualizado = True
            
            if callback_actualizar_ui:
                callback_actualizar_ui()
                
        threading.Thread(target=tarea, daemon=True).start()

class ServicioTiempo(ABC):
    @abstractmethod
    def obtener_datos_actuales(self) -> dict:
        pass

class RelojServicioTiempo(ServicioTiempo):
    def obtener_datos_actuales(self) -> dict:
        ahora = datetime.now()
        return {
            "hora_12": ahora.strftime("%I"),
            "minutos": ahora.strftime("%M"),
            "periodo": ahora.strftime("%p"),
            "dia": ahora.strftime("%d"),
            "mes": ahora.month,
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
        img = Image.new("RGB", (ancho, alto), "#050508")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        draw.ellipse([ancho * 0.1, alto * 0.1, ancho * 0.6, alto * 0.6], fill="#7000ff")
        draw.ellipse([ancho * 0.4, alto * 0.4, ancho * 0.85, alto * 0.85], fill="#00f2fe")
        
        img_difuminada = img.filter(ImageFilter.GaussianBlur(radius=55))
        
        resultado = ImageTk.PhotoImage(img_difuminada)
        return resultado

class VistaRelojMinimalista:
    def __init__(self, ventana: tk.Tk, servicio_tiempo: ServicioTiempo, evaluador: EvaluadorPeriodo):
        self._ventana = ventana
        self._servicio_tiempo = servicio_tiempo
        self._evaluador = evaluador
        self._archivo_temporal = "ctx_cache_bg.ps"
        self._clima = GestorClima()
        
        self._configurar_ventana()
        self._inicializar_componentes()
        
        self._clima.actualizar_datos(self._actualizar_datos_clima_ui)
        
        self._bucle_renderizado()
        self._programar_actualizacion_clima()

    def _configurar_ventana(self):
        self._ventana.title("Chronos Premium")
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

        self._lienzo.create_rectangle(40, 50, 360, 350, fill="#0d0e12", outline="#242836", width=2)

        self._lienzo.create_line(175, 70, 175, 330, fill="#ffb30a", width=3)

        self._lienzo.create_line(195, 200, 340, 200, fill="#ffb30a", width=2)

        self._lbl_am_pm = self._lienzo.create_text(
            60, 190, text="--", font=("Arial", 14, "bold"), fill="#a4a9b8"
        )
        self._lbl_hora = self._lienzo.create_text(
            118, 135, text="00", font=("Arial", 64, "bold"), fill="#ffffff"
        )
        self._lbl_minutos = self._lienzo.create_text(
            118, 245, text="00", font=("Arial", 64, "bold"), fill="#ffffff"
        )

        self._lbl_mes = self._lienzo.create_text(
            265, 105, text="MES", font=("Arial", 18, "bold"), fill="#a4a9b8"
        )
        self._lbl_dia = self._lienzo.create_text(
            265, 155, text="00", font=("Arial", 36, "bold"), fill="#ffffff"
        )

        self._lbl_ubicacion = self._lienzo.create_text(
            200, 230, text="📍 Cargando...", font=("Arial", 11, "bold"), fill="#ffffff", anchor="w"
        )
        self._lbl_clima = self._lienzo.create_text(
            200, 265, text="⏳ --", font=("Arial", 14, "bold"), fill="#ffb30a", anchor="w"
        )
        self._lbl_detalle = self._lienzo.create_text(
            200, 300, text="Obteniendo clima...", font=("Arial", 10), fill="#a4a9b8", anchor="w"
        )

    def _actualizar_datos_clima_ui(self):
        self._ventana.after(0, self._renderizar_clima)

    def _renderizar_clima(self):
        self._lienzo.itemconfig(self._lbl_ubicacion, text=f"📍 {self._clima.ciudad}, {self._clima.pais}")
        self._lienzo.itemconfig(self._lbl_clima, text=f"{self._clima.icono}  {self._clima.temperatura}")
        self._lienzo.itemconfig(self._lbl_detalle, text=self._clima.descripcion)

    def _programar_actualizacion_clima(self):
        def loop_clima():
            self._clima.actualizar_datos(self._actualizar_datos_clima_ui)
            self._ventana.after(1800000, loop_clima)
        self._ventana.after(1800000, loop_clima)

    def _bucle_renderizado(self):
        datos = self._servicio_tiempo.obtener_datos_actuales()
        
        nombre_mes = MESES.get(datos["mes"], "MES")
        
        self._lienzo.itemconfig(self._lbl_am_pm, text=datos["periodo"])
        self._lienzo.itemconfig(self._lbl_hora, text=datos["hora_12"])
        self._lienzo.itemconfig(self._lbl_minutos, text=datos["minutos"])
        self._lienzo.itemconfig(self._lbl_mes, text=nombre_mes)
        self._lienzo.itemconfig(self._lbl_dia, text=datos["dia"])
        
        self._ventana.after(1000, self._bucle_renderizado)

if __name__ == "__main__":
    root = tk.Tk()
    
    servicio = RelojServicioTiempo()
    analizador_periodo = EvaluadorPeriodo()
    
    app = VistaRelojMinimalista(root, servicio, analizador_periodo)
    root.mainloop()