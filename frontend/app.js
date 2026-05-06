// Configuración de URLs
const RAILWAY_URL = "https://microservicio-compras-production.up.railway.app/api/";
const LOCAL_URL = "http://localhost:8000/api/";

let API_BASE_URL = RAILWAY_URL; // Por defecto Railway

// Elementos del DOM principales
const tableHead = document.getElementById('table-head');
const tableBody = document.getElementById('table-body');
const pageTitle = document.getElementById('page-title');
const loadingSpinner = document.getElementById('loading-spinner');
const searchInput = document.getElementById('search-input');
const btnRefresh = document.getElementById('btn-refresh');
const navButtons = document.querySelectorAll('.nav-list button');
const btnAdd = document.getElementById('btn-add');

// Elementos Toggle
const envToggle = document.getElementById('env-toggle');
const envLabel = document.getElementById('env-label');

// Elementos CRUD Modal
const crudModal = document.getElementById('crud-modal');
const modalClose = document.getElementById('modal-close');
const btnCancel = document.getElementById('btn-cancel');
const btnSave = document.getElementById('btn-save');
const crudForm = document.getElementById('crud-form');
const modalTitle = document.getElementById('modal-title');

// Estado
let currentEndpoint = 'ordenes';
let currentData = [];
let isGenericQuery = false; // Si es una consulta genérica no se puede hacer POST/DELETE
let currentFieldsSchema = null;

// Reportes genéricos (para llenar el sidebar lateral)
const reportesGenericos = [
    { title: 'Join 2 Tablas (Proveedores/Catálogo)', url: 'proveedor-productos/join_dos_tablas' },
    { title: 'Join 3 Tablas (Prov/Prod/Catálogo)', url: 'proveedor-productos/join_tres_tablas' },
    { title: 'Req. Sin Órdenes', url: 'requisiciones/requisiciones_sin_ordenes' },
    { title: 'Órdenes por Área', url: 'requisiciones/ordenes_por_area' },
    { title: 'Cantidad por Requisición', url: 'ordenes/cantidad_por_requisicion' },
    { title: 'Gasto por Proveedor', url: 'ordenes/gasto_por_proveedor' },
    { title: 'Monto por Urgencia', url: 'ordenes/monto_total_por_urgencia' },
    { title: 'Órdenes Atrasadas', url: 'ordenes/ordenes_atrasadas' },
    { title: 'Alto Presupuesto (>10k)', url: 'ordenes/ordenes_alto_presupuesto' },
    { title: 'Sin Validación Financiera', url: 'ordenes/sin_validacion_financiera' },
    { title: 'Historial Validadas', url: 'ordenes/historial_validadas' },
    { title: 'Catálogo de Detalles', url: 'detalles-orden/catalogo_detalles' },
    { title: 'Detalles Urgentes', url: 'detalles-orden/detalles_urgentes' },
    { title: 'Gasto por Producto', url: 'detalles-orden/gasto_por_producto' },
    { title: 'Top 5 Productos', url: 'detalles-orden/top_productos_comprados' },
    { title: 'Controlados Pendientes', url: 'detalles-orden/productos_controlados_pedidos' },
    { title: 'Entregas sin Factura', url: 'recepciones/sin_factura' },
    { title: 'Entregas Inconformes', url: 'recepciones/inconformes' },
    { title: 'Presupuesto Bajo (<20%)', url: 'presupuestos/presupuesto_bajo' },
    { title: 'Resumen Ejecución (Gasto Real)', url: 'presupuestos/resumen_ejecucion' }
];

document.addEventListener('DOMContentLoaded', () => {
    // 1. Inicializar lista de reportes en el HTML
    const reportsNav = document.getElementById('reports-nav');
    reportesGenericos.forEach(rep => {
        const li = document.createElement('li');
        li.innerHTML = `<button data-endpoint="${rep.url}"><i class="fa-solid fa-file-contract"></i> ${rep.title}</button>`;
        reportsNav.appendChild(li);
    });

    // 2. Event Listeners para toda la barra lateral (Gestión y Reportes)
    document.querySelectorAll('.nav-list button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.nav-list button').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');

            currentEndpoint = e.currentTarget.getAttribute('data-endpoint');
            const title = e.currentTarget.innerText;
            
            // Si el endpoint tiene una barra "/", significa que es un "Action" (Consulta Genérica)
            isGenericQuery = currentEndpoint.includes('/');
            
            // Ocultar el botón "Agregar" si estamos viendo un reporte (no se puede agregar a un reporte)
            btnAdd.style.display = isGenericQuery ? 'none' : 'inline-flex';
            
            searchInput.value = '';
            loadData(currentEndpoint, title);
        });
    });

    // 3. Toggle Railway vs Localhost
    envToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            API_BASE_URL = RAILWAY_URL;
            envLabel.innerHTML = '<i class="fa-solid fa-cloud"></i> Railway';
            envLabel.className = 'status-badge online';
        } else {
            API_BASE_URL = LOCAL_URL;
            envLabel.innerHTML = '<i class="fa-solid fa-laptop-code"></i> Localhost';
            envLabel.className = 'status-badge local';
        }
        const activeBtn = document.querySelector('.nav-list button.active');
        loadData(currentEndpoint, activeBtn.innerText);
    });

    // 4. Botones simples
    btnRefresh.addEventListener('click', () => {
        const activeBtn = document.querySelector('.nav-list button.active');
        loadData(currentEndpoint, activeBtn.innerText);
    });

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredData = currentData.filter(item => 
            Object.values(item).some(val => String(val).toLowerCase().includes(searchTerm))
        );
        renderTable(filteredData);
    });

    // 5. CRUD Modal listeners
    btnAdd.addEventListener('click', openAddModal);
    modalClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);
    btnSave.addEventListener('click', saveNewRecord);

    // Cargar la vista por defecto
    loadData(currentEndpoint, "Órdenes de Compra");
});

// -- API Calls -- //

async function loadData(endpoint, title) {
    pageTitle.innerText = title;
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    loadingSpinner.style.display = 'flex';

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}/`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        currentData = await response.json();
        renderTable(currentData);
        
        // Si no es genérica, obtenemos el esquema (campos) de la tabla mediante OPTIONS para armar el form dinámico
        if (!isGenericQuery) {
            fetchSchema(endpoint);
        }
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="15" style="text-align:center; color:red; padding: 20px;">
            Error al conectar. Verifica que el backend esté ejecutándose (Railway o Local) y CORS permitido.<br>
            <small>${error.message}</small>
        </td></tr>`;
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

// Obtener la estructura de campos de Django REST (OPTIONS)
async function fetchSchema(endpoint) {
    try {
        const res = await fetch(`${API_BASE_URL}${endpoint}/`, { method: 'OPTIONS' });
        const data = await res.json();
        currentFieldsSchema = data.actions.POST; // Aquí DRF dice qué campos necesita
    } catch (e) {
        console.error("Error fetching schema", e);
    }
}

async function deleteRecord(id) {
    if (!confirm(`¿Estás seguro de que deseas eliminar (borrado lógico) el registro ${id}?`)) return;
    try {
        const res = await fetch(`${API_BASE_URL}${currentEndpoint}/${id}/`, { method: 'DELETE' });
        if (res.ok) {
            const activeBtn = document.querySelector('.nav-list button.active');
            loadData(currentEndpoint, activeBtn.innerText);
        } else {
            alert("Error al eliminar.");
        }
    } catch(e) { alert(e.message); }
}

async function saveNewRecord() {
    // Recolectar datos del formulario dinámico
    const formData = new FormData(crudForm);
    const jsonBody = {};
    
    for (let [key, value] of formData.entries()) {
        if (currentFieldsSchema[key].type === 'boolean') {
            jsonBody[key] = true; // Si está en el FormData, es true (checkbox checked)
        } else if (value.trim() === '') {
            jsonBody[key] = null; // Enviar nulos correctamente
        } else {
            jsonBody[key] = value;
        }
    }

    // Para checkboxes desmarcados, FormData no envía nada, debemos inyectar false
    Object.keys(currentFieldsSchema).forEach(key => {
        if (currentFieldsSchema[key].type === 'boolean' && !jsonBody.hasOwnProperty(key)) {
            jsonBody[key] = false;
        }
    });

    try {
        const res = await fetch(`${API_BASE_URL}${currentEndpoint}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jsonBody)
        });

        if (res.ok || res.status === 201) {
            closeModal();
            const activeBtn = document.querySelector('.nav-list button.active');
            loadData(currentEndpoint, activeBtn.innerText);
        } else {
            const errs = await res.json();
            alert("Errores de validación:\n" + JSON.stringify(errs, null, 2));
        }
    } catch(e) {
        alert("Error de conexión: " + e.message);
    }
}

// -- Renderizado UI -- //

function renderTable(data) {
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';

    if (!data || data.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="15" style="text-align:center; padding: 30px;">No hay datos para mostrar en esta sección.</td></tr>`;
        return;
    }

    const columns = Object.keys(data[0]);

    // Headers
    columns.forEach(col => {
        const th = document.createElement('th');
        th.innerText = col.replace(/_/g, ' ').toUpperCase();
        tableHead.appendChild(th);
    });

    // Columna de Acciones (Solo para tablas principales, NO para reportes)
    if (!isGenericQuery) {
        const thAcciones = document.createElement('th');
        thAcciones.innerText = "ACCIONES";
        tableHead.appendChild(thAcciones);
    }

    // Body
    data.forEach(item => {
        const tr = document.createElement('tr');
        let pkValue = null; // Necesitamos el ID para eliminar

        columns.forEach(col => {
            const td = document.createElement('td');
            let value = item[col];

            // Asumimos que la clave primaria (ID) es siempre el primer campo devuelto o uno que dice "codigo" o "periodo"
            if (col.startsWith('codigo') || col === 'periodo') {
                pkValue = value; 
            }

            if (value === null) {
                td.innerHTML = '<span class="badge-null">Ninguno</span>';
            } else if (typeof value === 'boolean') {
                td.innerHTML = value ? 'Sí' : 'No';
            } else {
                td.innerText = value;
            }
            tr.appendChild(td);
        });
        
        if (!isGenericQuery) {
            const tdAcciones = document.createElement('td');
            const btnDel = document.createElement('button');
            btnDel.className = 'btn-danger';
            btnDel.innerHTML = '<i class="fa-solid fa-trash"></i> Eliminar';
            btnDel.onclick = () => deleteRecord(pkValue);
            tdAcciones.appendChild(btnDel);
            tr.appendChild(tdAcciones);
        }

        tableBody.appendChild(tr);
    });
}

// -- Modal Genérico Construido con DRF Schema -- //
function openAddModal() {
    crudForm.innerHTML = ''; // Limpiar
    modalTitle.innerText = `Agregar a ${currentEndpoint.toUpperCase()}`;

    if (!currentFieldsSchema) {
        alert("El esquema aún no ha cargado o este endpoint no soporta inserción.");
        return;
    }

    Object.entries(currentFieldsSchema).forEach(([fieldName, fieldMeta]) => {
        if (fieldMeta.read_only) return; // No pedimos campos auto-generados o fechas automáticas

        const div = document.createElement('div');
        div.className = 'form-group';

        const label = document.createElement('label');
        label.innerText = fieldMeta.label || fieldName.replace(/_/g, ' ').toUpperCase();
        if (fieldMeta.required) label.innerText += ' *';
        div.appendChild(label);

        let input;
        if (fieldMeta.type === 'boolean') {
            input = document.createElement('input');
            input.type = 'checkbox';
        } else if (fieldMeta.type === 'string') {
            input = document.createElement('input');
            input.type = 'text';
            if (fieldMeta.max_length) input.maxLength = fieldMeta.max_length;
        } else if (fieldMeta.type === 'decimal' || fieldMeta.type === 'integer') {
            input = document.createElement('input');
            input.type = 'number';
            input.step = fieldMeta.type === 'decimal' ? '0.01' : '1';
        } else if (fieldMeta.type === 'choice') {
            input = document.createElement('select');
            fieldMeta.choices.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.value; opt.innerText = c.display_name;
                input.appendChild(opt);
            });
        } else {
            input = document.createElement('input');
            input.type = 'text';
        }

        input.name = fieldName;
        input.id = `input-${fieldName}`;
        if (fieldMeta.required) input.required = true;

        div.appendChild(input);
        crudForm.appendChild(div);
    });

    crudModal.style.display = 'block';
}

function closeModal() {
    crudModal.style.display = 'none';
}
