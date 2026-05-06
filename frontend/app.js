let API_BASE_URL = "/api/"; // Relativo a donde se hospeda

// Elementos del DOM principales
const tableHead = document.getElementById('table-head');
const tableBody = document.getElementById('table-body');
const pageTitle = document.getElementById('page-title');
const loadingSpinner = document.getElementById('loading-spinner');
const searchInput = document.getElementById('search-input');
const btnRefresh = document.getElementById('btn-refresh');
const navButtons = document.querySelectorAll('.nav-list button');
const btnAdd = document.getElementById('btn-add');

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
let isGenericQuery = false; 
let currentFieldsSchema = null;
let editingId = null; // Para saber si estamos editando (PUT) o creando (POST)

// Función para obtener el CSRF token de las cookies de Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const reportesGenericos = [
    { title: 'Catálogo Proveedor-Producto', url: 'proveedor-productos/join_dos_tablas' },
    { title: 'Detalle Completo de Catálogo', url: 'proveedor-productos/join_tres_tablas' },
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
    const reportsNav = document.getElementById('reports-nav');
    reportesGenericos.forEach(rep => {
        const li = document.createElement('li');
        li.innerHTML = `<button data-endpoint="${rep.url}"><i class="fa-solid fa-file-contract"></i> ${rep.title}</button>`;
        reportsNav.appendChild(li);
    });

    document.querySelectorAll('.nav-list button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.nav-list button').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');

            currentEndpoint = e.currentTarget.getAttribute('data-endpoint');
            const title = e.currentTarget.innerText;
            
            isGenericQuery = currentEndpoint.includes('/');
            btnAdd.style.display = isGenericQuery ? 'none' : 'inline-flex';
            
            searchInput.value = '';
            loadData(currentEndpoint, title);
        });
    });

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

    btnAdd.addEventListener('click', () => openModal());
    modalClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);
    btnSave.addEventListener('click', saveRecord);

    loadData(currentEndpoint, "Órdenes de Compra");
});

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
        
        if (!isGenericQuery) {
            fetchSchema(endpoint);
        }
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="15" style="text-align:center; color:red; padding: 20px;">
            Error al conectar. Verifica que el backend esté ejecutándose.<br>
            <small>${error.message}</small>
        </td></tr>`;
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

async function fetchSchema(endpoint) {
    try {
        const res = await fetch(`${API_BASE_URL}${endpoint}/`, { method: 'OPTIONS' });
        const data = await res.json();
        currentFieldsSchema = data.actions.POST; 
    } catch (e) {
        console.error("Error fetching schema", e);
    }
}

async function deleteRecord(id) {
    if (!confirm(`¿Estás seguro de que deseas eliminar el registro ${id}?`)) return;
    try {
        const res = await fetch(`${API_BASE_URL}${currentEndpoint}/${id}/`, { 
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        if (res.ok) {
            const activeBtn = document.querySelector('.nav-list button.active');
            loadData(currentEndpoint, activeBtn.innerText);
        } else {
            alert("Error al eliminar.");
        }
    } catch(e) { alert(e.message); }
}

async function solicitarAprobacionLegal(id) {
    if (!confirm(`¿Solicitar aprobación legal a la API externa para la orden ${id}?`)) return;
    try {
        const res = await fetch(`${API_BASE_URL}ordenes/${id}/solicitar_legal/`, { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        const data = await res.json();
        if (res.ok) {
            alert("Aprobación Legal:\n" + (data.mensaje || "Éxito") + "\nToken: " + (data.token_legal || "Ninguno"));
            const activeBtn = document.querySelector('.nav-list button.active');
            loadData(currentEndpoint, activeBtn.innerText);
        } else {
            alert("Error en Legal:\n" + (data.error || data.detail || data.mensaje || JSON.stringify(data)));
            const activeBtn = document.querySelector('.nav-list button.active');
            loadData(currentEndpoint, activeBtn.innerText);
        }
    } catch(e) { alert(e.message); }
}

async function saveRecord() {
    const formData = new FormData(crudForm);
    const jsonBody = {};
    
    for (let [key, value] of formData.entries()) {
        if (currentFieldsSchema[key].type === 'boolean') {
            jsonBody[key] = true;
        } else if (value.trim() === '') {
            jsonBody[key] = null;
        } else {
            jsonBody[key] = value;
        }
    }

    Object.keys(currentFieldsSchema).forEach(key => {
        if (currentFieldsSchema[key].type === 'boolean' && !jsonBody.hasOwnProperty(key)) {
            jsonBody[key] = false;
        }
    });

    const url = editingId ? `${API_BASE_URL}${currentEndpoint}/${editingId}/` : `${API_BASE_URL}${currentEndpoint}/`;
    const method = editingId ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') 
            },
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

function renderTable(data) {
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';

    if (!data || data.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="15" style="text-align:center; padding: 30px;">No hay datos para mostrar en esta sección.</td></tr>`;
        return;
    }

    const columns = Object.keys(data[0]);

    columns.forEach(col => {
        const th = document.createElement('th');
        th.innerText = col.replace(/_/g, ' ').toUpperCase();
        tableHead.appendChild(th);
    });

    if (!isGenericQuery) {
        const thAcciones = document.createElement('th');
        thAcciones.innerText = "ACCIONES";
        tableHead.appendChild(thAcciones);
    }

    data.forEach(item => {
        const tr = document.createElement('tr');
        let pkValue = item[columns[0]]; // La primera columna siempre es el PK (código)

        columns.forEach(col => {
            const td = document.createElement('td');
            let value = item[col];

            if (value === null || value === undefined) {
                td.innerHTML = '<span class="badge-null">—</span>';
            } else if (typeof value === 'boolean') {
                td.innerHTML = value 
                    ? '<span style="color:#22c55e;font-weight:600;">✔ Sí</span>' 
                    : '<span style="color:#ef4444;font-weight:600;">✘ No</span>';
            } else if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
                // Formatear fechas ISO → dd/mm/yyyy HH:MM
                const fecha = new Date(value);
                td.innerText = fecha.toLocaleDateString('es-BO', {
                    day: '2-digit', month: '2-digit', year: 'numeric'
                }) + ' ' + fecha.toLocaleTimeString('es-BO', {
                    hour: '2-digit', minute: '2-digit'
                });
            } else {
                td.innerText = value;
            }
            tr.appendChild(td);
        });
        
        if (!isGenericQuery) {
            const tdAcciones = document.createElement('td');
            tdAcciones.style.display = 'flex';
            tdAcciones.style.gap = '5px';

            const btnEdit = document.createElement('button');
            btnEdit.className = 'btn-secondary';
            btnEdit.style.padding = '6px 10px';
            btnEdit.style.fontSize = '0.8rem';
            btnEdit.innerHTML = '<i class="fa-solid fa-pen"></i> Editar';
            btnEdit.onclick = () => openModal(item, pkValue);

            const btnDel = document.createElement('button');
            btnDel.className = 'btn-danger';
            btnDel.innerHTML = '<i class="fa-solid fa-trash"></i> Eliminar';
            btnDel.onclick = () => deleteRecord(pkValue);
            
            tdAcciones.appendChild(btnEdit);
            tdAcciones.appendChild(btnDel);

            // Si estamos en la tabla Órdenes, agregar botón "Solicitar Legal"
            if (currentEndpoint === 'ordenes') {
                const btnLegal = document.createElement('button');
                btnLegal.className = 'btn-success';
                btnLegal.style.padding = '6px 10px';
                btnLegal.style.fontSize = '0.8rem';
                btnLegal.innerHTML = '<i class="fa-solid fa-gavel"></i> Legal';
                btnLegal.onclick = () => solicitarAprobacionLegal(pkValue);
                tdAcciones.appendChild(btnLegal);
            }

            tr.appendChild(tdAcciones);
        }

        tableBody.appendChild(tr);
    });
}

function openModal(itemData = null, pk = null) {
    crudForm.innerHTML = '';
    editingId = pk;
    modalTitle.innerText = editingId ? `Editar ${currentEndpoint.toUpperCase()}` : `Agregar a ${currentEndpoint.toUpperCase()}`;

    if (!currentFieldsSchema) {
        alert("El esquema aún no ha cargado o este endpoint no soporta inserción.");
        return;
    }

    Object.entries(currentFieldsSchema).forEach(([fieldName, fieldMeta]) => {
        if (fieldMeta.read_only) return; 

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
            if (itemData && itemData[fieldName]) input.checked = true;
        } else if (fieldMeta.type === 'choice') {
            input = document.createElement('select');
            fieldMeta.choices.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.value; opt.innerText = c.display_name;
                input.appendChild(opt);
            });
            if (itemData && itemData[fieldName]) input.value = itemData[fieldName];
        } else if (fieldMeta.type === 'datetime' || fieldMeta.type === 'date') {
            input = document.createElement('input');
            input.type = fieldMeta.type === 'datetime' ? 'datetime-local' : 'date';
            if (itemData && itemData[fieldName]) {
                const rawDate = new Date(itemData[fieldName]);
                if (!isNaN(rawDate)) {
                    // Convertir UTC a hora LOCAL del navegador para que el usuario vea/edite la hora correcta
                    const localISO = new Date(rawDate.getTime() - rawDate.getTimezoneOffset() * 60000)
                        .toISOString().substring(0, 16);
                    input.value = localISO;
                }
            }
        } else {
            input = document.createElement('input');
            input.type = fieldMeta.type === 'decimal' || fieldMeta.type === 'integer' ? 'number' : 'text';
            if (fieldMeta.type === 'decimal') input.step = '0.01';
            if (fieldMeta.max_length) input.maxLength = fieldMeta.max_length;
            if (itemData && itemData[fieldName]) input.value = itemData[fieldName];
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
    editingId = null;
}
