// Funcionalidades generales de la aplicación
document.addEventListener('DOMContentLoaded', function () {
    // Inicializar tooltips
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });

    // Sistema de tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const target = this.getAttribute('data-target');

            // Desactivar todas las pestañas
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));

            // Activar la pestaña seleccionada
            this.classList.add('active');
            document.querySelector(target).classList.add('active');
        });
    });

    // Actualizar contador del carrito
    updateCartCount();

    // Manejar modales
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        const closeBtn = modal.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }
    });

    // Cerrar modal al hacer clic fuera
    window.addEventListener('click', function (event) {
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Inicializar funcionalidades específicas de página
    if (document.getElementById('plato-customization')) {
        initPlatoCustomization();
    }

    if (document.getElementById('checkout-form')) {
        initCheckoutForm();
    }

    if (document.getElementById('admin-productos')) {
        initAdminProductos();
    }

    if (document.getElementById('geolocation-btn')) {
        initGeolocation();
    }
});

// Función para actualizar el contador del carrito
function updateCartCount() {
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        fetch('/api/carrito')
            .then(response => response.json())
            .then(data => {
                cartCount.textContent = data.count;
                // Si no hay items, ocultar el contador
                cartCount.style.display = data.count > 0 ? 'flex' : 'none';
            })
            .catch(error => console.error('Error:', error));
    }
}

// Función para agregar al carrito
function addToCart(platoId, personalizaciones = {}) {
    const formData = new FormData();
    formData.append('plato_id', platoId);
    formData.append('personalizaciones', JSON.stringify(personalizaciones));

    fetch(`/agregar_carrito/${platoId}`, {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCartCount();
                showAlert('Plato agregado al carrito', 'success');

                // Mostrar modal de carrito si está en la página de menú
                if (window.location.pathname === '/menu') {
                    const cartModal = new bootstrap.Modal(document.getElementById('cartModal'));
                    cartModal.show();
                }
            } else {
                showAlert('Error al agregar al carrito', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error al agregar al carrito', 'error');
        });
}

// Función para actualizar cantidad en el carrito
function updateCartItem(index, cantidad) {
    fetch('/actualizar_carrito', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ item_index: index, cantidad: cantidad })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCartCount();
                // Recargar la página para reflejar los cambios
                location.reload();
            } else {
                showAlert('Error al actualizar el carrito', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error al actualizar el carrito', 'error');
        });
}

// Función para eliminar item del carrito
function removeCartItem(index) {
    updateCartItem(index, 0);
}

// Función para mostrar alertas
function showAlert(message, type = 'info') {
    // Crear elemento de alerta
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} fade-in`;
    alertDiv.textContent = message;

    // Agregar botón de cierre
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    alertDiv.appendChild(closeButton);

    // Insertar en el DOM
    const container = document.querySelector('.alert-container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);

    // Eliminar después de 5 segundos
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Personalización de platos
function initPlatoCustomization() {
    const customizationForm = document.getElementById('plato-customization');
    if (!customizationForm) return;

    const platoId = customizationForm.getAttribute('data-plato-id');
    const extras = customizationForm.querySelectorAll('.extra-option');
    const personalizaciones = {};

    extras.forEach(extra => {
        extra.addEventListener('change', function () {
            const extraId = this.getAttribute('data-extra-id');
            const extraPrecio = parseFloat(this.getAttribute('data-extra-precio'));

            if (this.checked) {
                personalizaciones[extraId] = {
                    nombre: this.getAttribute('data-extra-nombre'),
                    precio: extraPrecio
                };
            } else {
                delete personalizaciones[extraId];
            }

            // Actualizar precio total
            updateCustomizationPrice(personalizaciones);
        });
    });

    // Botón de agregar al carrito
    const addToCartBtn = customizationForm.querySelector('.add-to-cart-btn');
    if (addToCartBtn) {
        addToCartBtn.addEventListener('click', function () {
            addToCart(platoId, personalizaciones);
        });
    }
}

function updateCustomizationPrice(personalizaciones) {
    const basePriceElement = document.getElementById('plato-base-price');
    const totalPriceElement = document.getElementById('plato-total-price');

    if (!basePriceElement || !totalPriceElement) return;

    const basePrice = parseFloat(basePriceElement.getAttribute('data-base-price'));
    let extrasTotal = 0;

    for (const extraId in personalizaciones) {
        extrasTotal += personalizaciones[extraId].precio;
    }

    const totalPrice = basePrice + extrasTotal;
    totalPriceElement.textContent = totalPrice.toFixed(2);
}

// Formulario de checkout
function initCheckoutForm() {
    const checkoutForm = document.getElementById('checkout-form');
    if (!checkoutForm) return;

    // Rellenar datos guardados si existen
    const savedPhone = getCookie('cliente_telefono');
    const savedAddress = getCookie('cliente_direccion');
    const savedName = getCookie('cliente_nombre');

    if (savedPhone) checkoutForm.querySelector('input[name="telefono"]').value = savedPhone;
    if (savedAddress) checkoutForm.querySelector('input[name="direccion"]').value = savedAddress;
    if (savedName) checkoutForm.querySelector('input[name="nombre"]').value = savedName;

    // Validación del formulario
    checkoutForm.addEventListener('submit', function (e) {
        let isValid = true;
        const telefono = this.querySelector('input[name="telefono"]');
        const direccion = this.querySelector('input[name="direccion"]');
        const ubicacion = this.querySelector('input[name="ubicacion"]');

        if (!telefono.value.trim()) {
            showFieldError(telefono, 'El teléfono es obligatorio');
            isValid = false;
        } else {
            clearFieldError(telefono);
        }

        if (!direccion.value.trim()) {
            showFieldError(direccion, 'La dirección es obligatoria');
            isValid = false;
        } else {
            clearFieldError(direccion);
        }

        if (!ubicacion.value.trim()) {
            showFieldError(ubicacion, 'Debe obtener su ubicación');
            isValid = false;
        } else {
            clearFieldError(ubicacion);
        }

        if (!isValid) {
            e.preventDefault();
            showAlert('Por favor, complete todos los campos obligatorios', 'error');
        }
    });
}

// Geolocalización
function initGeolocation() {
    const geoBtn = document.getElementById('geolocation-btn');
    const locationField = document.getElementById('ubicacion');

    if (!geoBtn || !locationField) return;

    geoBtn.addEventListener('click', function () {
        if (!navigator.geolocation) {
            showAlert('La geolocalización no es compatible con su navegador', 'error');
            return;
        }

        geoBtn.disabled = true;
        geoBtn.innerHTML = '<span class="loader"></span> Obteniendo ubicación...';

        navigator.geolocation.getCurrentPosition(
            function (position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                // Usar Nominatim para reverse geocoding
                fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`)
                    .then(response => response.json())
                    .then(data => {
                        const address = data.display_name;
                        locationField.value = address;

                        // Guardar también las coordenadas en un campo oculto
                        let coordsField = document.getElementById('coordenadas');
                        if (!coordsField) {
                            coordsField = document.createElement('input');
                            coordsField.type = 'hidden';
                            coordsField.name = 'coordenadas';
                            coordsField.id = 'coordenadas';
                            locationField.parentNode.appendChild(coordsField);
                        }
                        coordsField.value = `${lat},${lng}`;

                        geoBtn.disabled = false;
                        geoBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Obtener ubicación';
                        showAlert('Ubicación obtenida correctamente', 'success');
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        locationField.value = `${lat}, ${lng}`;
                        geoBtn.disabled = false;
                        geoBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Obtener ubicación';
                        showAlert('Ubicación obtenida (sin dirección)', 'info');
                    });
            },
            function (error) {
                console.error('Error obteniendo ubicación:', error);
                geoBtn.disabled = false;
                geoBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Obtener ubicación';

                let errorMsg = 'Error al obtener la ubicación';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Permiso de ubicación denegado';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Información de ubicación no disponible';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Tiempo de espera agotado';
                        break;
                }

                showAlert(errorMsg, 'error');
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    });
}

// Funciones para administración de productos
function initAdminProductos() {
    // Eliminar producto con confirmación
    const deleteButtons = document.querySelectorAll('.delete-producto-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const productId = this.getAttribute('data-id');
            const productName = this.getAttribute('data-name');

            if (confirm(`¿Está seguro de que desea eliminar el producto "${productName}"?`)) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/admin/producto/eliminar/${productId}`;

                const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
                const tokenInput = document.createElement('input');
                tokenInput.type = 'hidden';
                tokenInput.name = 'csrf_token';
                tokenInput.value = csrfToken;
                form.appendChild(tokenInput);

                document.body.appendChild(form);
                form.submit();
            }
        });
    });

    // Calcular costo de plato en tiempo real
    const calcularCostoBtn = document.getElementById('calcular-costo-btn');
    if (calcularCostoBtn) {
        calcularCostoBtn.addEventListener('click', function () {
            const ingredientes = [];
            let i = 0;

            while (true) {
                const productoId = document.querySelector(`[name="producto_id_${i}"]`);
                const cantidad = document.querySelector(`[name="cantidad_${i}"]`);

                if (!productoId || !cantidad) break;

                if (productoId.value && cantidad.value) {
                    ingredientes.push({
                        producto_id: parseInt(productoId.value),
                        cantidad: parseFloat(cantidad.value)
                    });
                }

                i++;
            }

            if (ingredientes.length === 0) {
                showAlert('Agregue al menos un ingrediente', 'error');
                return;
            }

            fetch('/admin/calcular_costo_plato', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ ingredientes: ingredientes })
            })
                .then(response => response.json())
                .then(data => {
                    const costoElement = document.getElementById('costo-plato');
                    const gananciaElement = document.getElementById('ganancia-plato');
                    const precioVentaElement = document.querySelector('[name="precio_venta"]');

                    if (costoElement) {
                        costoElement.textContent = data.costo.toFixed(2);
                    }

                    if (gananciaElement && precioVentaElement && precioVentaElement.value) {
                        const precioVenta = parseFloat(precioVentaElement.value);
                        const ganancia = precioVenta - data.costo;
                        gananciaElement.textContent = ganancia.toFixed(2);

                        // Cambiar color según la ganancia
                        if (ganancia < 0) {
                            gananciaElement.style.color = 'var(--danger-color)';
                        } else if (ganancia < data.costo * 0.5) {
                            gananciaElement.style.color = 'var(--warning-color)';
                        } else {
                            gananciaElement.style.color = 'var(--success-color)';
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('Error al calcular el costo', 'error');
                });
        });
    }
}

// Funciones auxiliares
function showFieldError(field, message) {
    clearFieldError(field);

    field.classList.add('is-invalid');

    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;

    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');

    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Funciones para el sistema de tabs en administración
function openTab(tabName) {
    const tabs = document.querySelectorAll('.admin-tab');
    tabs.forEach(tab => {
        tab.style.display = 'none';
    });

    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });

    document.getElementById(tabName).style.display = 'block';
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

// Inicializar mapas si es necesario
function initMap() {
    if (typeof L !== 'undefined' && document.getElementById('map')) {
        const map = L.map('map').setView([0, 0], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        const marker = L.marker([0, 0]).addTo(map);

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function (position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                map.setView([lat, lng], 15);
                marker.setLatLng([lat, lng]);

                // Actualizar campo de ubicación
                const ubicacionField = document.getElementById('ubicacion');
                if (ubicacionField) {
                    ubicacionField.value = `${lat}, ${lng}`;
                }
            });
        }

        map.on('click', function (e) {
            marker.setLatLng(e.latlng);

            const ubicacionField = document.getElementById('ubicacion');
            if (ubicacionField) {
                ubicacionField.value = `${e.latlng.lat}, ${e.latlng.lng}`;
            }
        });
    }
}

// Exportar funciones para uso global
window.addToCart = addToCart;
window.updateCartItem = updateCartItem;
window.removeCartItem = removeCartItem;
window.showAlert = showAlert;
window.openTab = openTab;
window.initMap = initMap;