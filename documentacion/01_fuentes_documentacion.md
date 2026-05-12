# 01 — Fuentes de documentación

Todo lo que necesitas saber sobre dónde encontrar información oficial y comunitaria del Unitree Go2.

---

## Documentación oficial de Unitree

| Recurso | URL | Notas |
|---|---|---|
| Portal de desarrolladores | https://support.unitree.com/home/en/developer | Guías oficiales del Go2 SDK |
| SDK oficial C++ (unitree_sdk2) | https://github.com/unitreerobotics/unitree_sdk2 | Soporta Go2, B2, H1, G1 |
| SDK oficial Python | https://github.com/unitreerobotics/unitree_sdk2_python | Wrapper Python del SDK C++ |
| SDK ROS2 oficial | https://github.com/unitreerobotics/unitree_ros2 | Para entornos ROS2 |
| Manual de usuario Go2 (PDF) | https://static.generation-robots.com/media/Go2-User-Manual.pdf | Modos de operación físicos |
| Docs del sport_client (C++) | https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/go2/sport/sport_client.hpp | Fuente directa de todos los métodos |

---

## Librerías de conexión WebRTC (las que usamos en este proyecto)

Estas son las más relevantes para conectarse por **WiFi sin jailbreak**, que es nuestro caso en DUOC UC.

### `unitree_webrtc_connect` (recomendada)

- **Repo**: https://github.com/legion1581/unitree_webrtc_connect
- **PyPI**: `pip install go2-webrtc-connect`
- **Compatible con**: Air, Pro y EDU — sin modificación de firmware
- **Protocolo**: el mismo WebRTC que usa la app oficial Unitree Go
- **Capacidades**: movimientos, cámara, LiDAR, audio (Pro/EDU)

### `go2-webrtc` (referencia original)

- **Repo**: https://github.com/tfoldi/go2-webrtc
- Fue el primer proyecto WebRTC para Go2, base de los demás
- Tiene ejemplos en JavaScript y Python

### `go2_python_sdk` (alternativa DDS)

- **Repo**: https://github.com/legion1581/go2_python_sdk
- Usa CycloneDDS en lugar de WebRTC
- Funciona sin modificación solo en EDU; Air/Pro necesitan firmware custom
- Más completo pero más complejo de configurar

---

## SDKs de ROS2 no oficiales (referencia, no usados en este proyecto)

| Recurso | URL |
|---|---|
| go2_ros2_sdk (WebRTC + DDS) | https://github.com/abizovnuralem/go2_ros2_sdk |
| go2_webrtc_connect (fork de phospho) | https://github.com/phospho-app/go2_webrtc_connect |
| unitree_sdk Go2+G1 ROS2 | https://github.com/OpenMind/unitree-sdk |

---

## Comunidad y recursos adicionales

| Recurso | URL | Para qué sirve |
|---|---|---|
| TheRoboVerse (comunidad Go2) | https://www.theroboverse.com | Foro, Discord, hacks, firmware |
| Wiki TheRoboVerse | https://wiki.theroboverse.com | Comandos de la app, jailbreak, tips |
| Docs del Go2 en ReadTheDocs | https://unitree-docs.readthedocs.io | Documentación Go1/Go2 SDK legacy |
| Docs cuadruped.de (Go2) | https://www.docs.quadruped.de/projects/go2/html/ | Guía completa en inglés del Go2 |
| Go2 Agent SDK (referencia de arquitectura) | https://github.com/grasp-lyrl/unitree_go2w_agent_sdk | Ejemplo de agente IA con el Go2 |

---

## Qué leer primero (orden recomendado)

1. Manual de usuario Go2 — para entender físicamente el robot y sus modos
2. `sport_client.hpp` — para ver todos los métodos disponibles en C++ (base de las tools)
3. README de `unitree_webrtc_connect` — para entender cómo conectarse
4. Ejemplos en `/examples` del repo de la librería WebRTC
5. Portal oficial de Unitree — para la guía de desarrollo del SDK2
