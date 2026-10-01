"""
App Streamlit mejorada:
- Subnetting
- Topología con visualización interactiva (pyvis)
- Generación de configuraciones con preview por nodo y descarga ZIP
- Control de versiones local (workspace + git)
"""

import streamlit as st
import pandas as pd
import json
import io
import zipfile
import os
import streamlit.components.v1 as components

from subnetting import split_network, split_into_n_subnets
from topology import parse_topology_csv, parse_topology_json, TopologyError
from network_config import generate_vendor_configs
import git_utils

st.set_page_config(page_title="Herramienta Redes WAN (GUI)", layout="wide")
st.title("Herramienta de Diseño y Gestión WAN — Interfaz Gráfica")

# Sidebar: elegir módulo
module = st.sidebar.selectbox("Módulo", ["Subnetting", "Topología", "Configuración", "Control de versiones"])

if module == "Subnetting":
    st.header("Subnetting")
    st.write("Corta una red en subredes más pequeñas (IPv4).")

    col1, col2 = st.columns([2,1])
    with col1:
        network_input = st.text_input("Red (CIDR)", value="192.168.0.0/24")
    with col2:
        mode = st.selectbox("Modo", ["Dividir por prefijo", "Dividir en N subredes"])

    if mode == "Dividir por prefijo":
        new_prefix = st.number_input("Nuevo prefijo (ej. 26)", min_value=0, max_value=32, value=26)
        if st.button("Calcular subredes"):
            try:
                entries = split_network(network_input, int(new_prefix))
                df = pd.DataFrame(entries)
                st.dataframe(df)
                st.download_button("Descargar CSV", df.to_csv(index=False), file_name="subnets.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        n_subnets = st.number_input("Número de subredes", min_value=1, value=4)
        if st.button("Calcular N subredes"):
            try:
                entries = split_into_n_subnets(network_input, int(n_subnets))
                df = pd.DataFrame(entries)
                st.dataframe(df)
                st.download_button("Descargar CSV", df.to_csv(index=False), file_name="subnets_n.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Error: {e}")

elif module == "Topología":
    st.header("Carga y visualización de Topología (GUI)")
    st.write("Sube un CSV o JSON con nodos, interfaces y direcciones IP. Visualización interactiva incluida.")

    uploaded = st.file_uploader("Sube CSV o JSON de topología", type=["csv", "json"])

    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                topo = parse_topology_csv(uploaded)
            else:
                topo = parse_topology_json(uploaded)

            st.success("Topología validada correctamente.")
            st.sidebar.subheader("Resumen")
            st.sidebar.write(topo.summary())

            nodes_df, links_df = topo.to_tables()
            st.subheader("Nodos e interfaces")
            st.dataframe(nodes_df)
            st.subheader("Enlaces")
            st.dataframe(links_df)

            try:
                pyvis_html = topo.to_pyvis_html(height="600px", width="100%")
                st.subheader("Visualización interactiva")
                components.html(pyvis_html, height=650, scrolling=True)
            except Exception as e:
                st.warning(f"No se pudo generar la visualización interactiva: {e}")
                try:
                    st.graphviz_chart(topo.to_dot())
                except Exception:
                    st.info("Graphviz no disponible.")

            st.markdown("---")
            st.subheader("Exportar topología validada")
            if st.button("Descargar JSON de topología validada"):
                topo_json = {
                    "nodes": [
                        {"name": n, "interfaces": [{"name": iface, "ip": ip} for iface, ip in info["interfaces"].items()]}
                        for n, info in topo.nodes.items()
                    ],
                    "links": [{"node_a": a, "if_a": ia, "node_b": b, "if_b": ib} for a,ia,b,ib in topo.links]
                }
                st.download_button("Descargar JSON", json.dumps(topo_json, indent=2), file_name="topology_validated.json", mime="application/json")

        except TopologyError as te:
            st.error(f"Error en topología: {te}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")

elif module == "Configuración":
    st.header("Generación de configuraciones (GUI)")
    st.write("Carga primero una topología válida (CSV/JSON). Luego elige fabricante y genera configs interactivamente.")

    uploaded = st.file_uploader("Sube la topología (CSV o JSON)", type=["csv", "json"], key="cfg_upload")
    vendor = st.selectbox("Fabricante", ["Cisco", "Huawei"], index=0)

    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                topo = parse_topology_csv(uploaded)
            else:
                topo = parse_topology_json(uploaded)

            st.success("Topología validada — lista para generar configuraciones.")
            st.info("Selecciona nodos en el desplegable para ver su configuración. Puedes descargar todas en un ZIP.")

            configs = generate_vendor_configs(topo, vendor.lower())

            node_list = sorted(configs.keys())
            selected_node = st.selectbox("Selecciona un nodo para ver su config", ["-- ninguno --"] + node_list)
            if selected_node and selected_node != "-- ninguno --":
                st.subheader(f"Configuración: {selected_node}")
                st.code(configs[selected_node], language="text")
                st.download_button(f"Descargar {selected_node}.cfg", configs[selected_node], file_name=f"{selected_node}_{vendor}.cfg", mime="text/plain")

            st.markdown("---")
            if st.button("Descargar todas las configuraciones (ZIP)"):
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
                    for node, cfg in configs.items():
                        filename = f"{node}_{vendor}.cfg"
                        z.writestr(filename, cfg)
                buffer.seek(0)
                st.download_button("Descargar ZIP", data=buffer, file_name=f"configs_{vendor}.zip", mime="application/zip")

            st.subheader("Todas las configuraciones")
            for node, cfg in configs.items():
                with st.expander(node):
                    st.code(cfg, language="text")

        except TopologyError as e:
            st.error(f"Error en la topología: {e}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")

else:  # Control de versiones
    st.header("Control de versiones local (git) — Workspace seguro")
    st.write("Guarda topologías y configuraciones en un workspace versionado localmente. No hacemos push a remotos automáticamente.")

    workspace_dir = os.path.join(os.getcwd(), "workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    st.write(f"Workspace: {workspace_dir}")

    try:
        repo_present = git_utils.is_git_repo(workspace_dir)
    except Exception as e:
        st.error(f"Error comprobando Git: {e}")
        repo_present = False

    col_init, col_status = st.columns([1,2])
    with col_init:
        if not repo_present:
            if st.button("Inicializar repo Git en workspace"):
                try:
                    msg = git_utils.git_init(workspace_dir)
                    st.success(msg)
                    repo_present = True
                except Exception as e:
                    st.error(f"No se pudo inicializar repo: {e}")
        else:
            st.success("Workspace ya es un repositorio Git local.")

    with col_status:
        if repo_present:
            try:
                status = git_utils.git_status(workspace_dir)
                st.text_area("Estado Git (porcelain -b)", value=status or "(limpio)", height=120)
            except Exception as e:
                st.error(f"Error al obtener estado: {e}")

    st.markdown("---")
    st.subheader("Guardar topología validada en workspace")
    uploaded = st.file_uploader("Sube topología CSV o JSON para guardar/versionar", type=["csv", "json"], key="vcs_topo")
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                topo = parse_topology_csv(uploaded)
            else:
                topo = parse_topology_json(uploaded)
            st.success("Topología validada. Puedes guardarla en workspace y commitearla.")
            topology_path = os.path.join(workspace_dir, "topology_validated.json")
            with open(topology_path, "w", encoding="utf-8") as f:
                topo_json = {
                    "nodes": [
                        {"name": n, "interfaces": [{"name": iface, "ip": ip} for iface, ip in info["interfaces"].items()]}
                        for n, info in topo.nodes.items()
                    ],
                    "links": [{"node_a": a, "if_a": ia, "node_b": b, "if_b": ib} for a,ia,b,ib in topo.links]
                }
                json.dump(topo_json, f, indent=2)
            st.write(f"Topología guardada en: {topology_path}")

            if st.button("Añadir y commitear topología (workspace)"):
                if not git_utils.is_git_repo(workspace_dir):
                    st.error("Inicializa el repo primero.")
                else:
                    commit_msg = st.text_input("Mensaje del commit", value="Guardar topología validada")
                    if commit_msg:
                        try:
                            res = git_utils.git_add_and_commit(workspace_dir, commit_msg, files=["topology_validated.json"])
                            st.success(f"Commit: {res}")
                        except Exception as e:
                            st.error(f"Error en commit: {e}")
                    else:
                        st.info("Escribe un mensaje de commit antes de confirmar.")

        except TopologyError as te:
            st.error(f"Topología inválida: {te}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")

    st.markdown("---")
    st.subheader("Guardar y commitear configuraciones generadas")
    uploaded2 = st.file_uploader("Sube topología para generar configs", type=["csv","json"], key="vcs_configs")
    vendor = st.selectbox("Fabricante para configs", ["Cisco", "Huawei"], key="vcs_vendor")

    if uploaded2 is not None:
        try:
            if uploaded2.name.lower().endswith(".csv"):
                topo2 = parse_topology_csv(uploaded2)
            else:
                topo2 = parse_topology_json(uploaded2)
            configs = generate_vendor_configs(topo2, vendor.lower())

            configs_dir = os.path.join(workspace_dir, "configs", vendor.lower())
            os.makedirs(configs_dir, exist_ok=True)
            for node, cfg in configs.items():
                file_path = os.path.join(configs_dir, f"{node}_{vendor}.cfg")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(cfg)

            st.success(f"Configs guardadas en {configs_dir}")
            st.write("Archivos guardados:")
            for f in sorted(os.listdir(configs_dir)):
                st.write(f"- {f}")

            if st.button("Añadir y commitear configs (workspace)"):
                if not git_utils.is_git_repo(workspace_dir):
                    st.error("Inicializa el repo primero.")
                else:
                    commit_msg_cfg = st.text_input("Mensaje de commit para configs", value=f"Add configs {vendor}")
                    if commit_msg_cfg:
                        try:
                            res = git_utils.git_add_and_commit(workspace_dir, commit_msg_cfg, files=[f"configs/{vendor.lower()}"])
                            st.success(f"Commit: {res}")
                        except Exception as e:
                            st.error(f"Error en commit: {e}")
                    else:
                        st.info("Escribe un mensaje de commit antes de confirmar.")

        except TopologyError as te:
            st.error(f"Topología inválida: {te}")
        except Exception as e:
            st.error(f"Error inesperado: {e}")

    st.markdown("---")
    st.subheader("Operaciones Git adicionales (locales)")
    if repo_present:
        try:
            log = git_utils.git_log(workspace_dir, max_entries=50)
            st.text_area("Git log (oneline)", value=log or "(sin commits aún)", height=180)
        except Exception as e:
            st.error(f"No se pudo leer log: {e}")

    st.write("Advertencia: Esta UI sólo realiza operaciones locales. Para subir a GitHub o remoto, hazlo desde tu terminal (ssh keys o PAT). No gestionamos credenciales aquí.")
