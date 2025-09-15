// Hotels page scoped JS - Now works on any page with hotel forms
(function(){
    function initHotelsPage(){
        console.log('🎯 Hotels JS: Initializing...');
        
        // Check if we're on a hotel form page
        const otasyncToggle = document.querySelector('input[name="otasync_enabled"]');
        if (!otasyncToggle) {
            console.log('⚠️ Hotels JS: No OTASync toggle found, not a hotel form page');
            return;
        }
        
        console.log('✅ Hotels JS: Hotel form detected, continuing...');

        // Handle OTASync integration toggle
        console.log('🎯 OTASync toggle found:', !!otasyncToggle);
        
        if (otasyncToggle) {
            function toggleOTASyncFields() {
                console.log('🎯 Toggle clicked, state:', otasyncToggle.checked);
                
                // Buscar TODOS los elementos con clase otasync-field
                const otasyncFields = document.querySelectorAll('.otasync-field');
                console.log('🎯 Found .otasync-field elements:', otasyncFields.length);
                
                // También buscar elementos específicos por contenido
                const propertyDiv = document.querySelector('select[name="otasync_property_id"]')?.closest('.col-md-6');
                const pricingRow = document.querySelector('input[name="otasync_pricing_plan_id"]')?.closest('.row');
                
                console.log('🎯 Property div found:', !!propertyDiv);
                console.log('🎯 Pricing row found:', !!pricingRow);
                
                const allElements = [...otasyncFields];
                if (propertyDiv && !allElements.includes(propertyDiv)) allElements.push(propertyDiv);
                if (pricingRow && !allElements.includes(pricingRow)) allElements.push(pricingRow);
                
                console.log('🎯 Total elements to show/hide:', allElements.length);
                
                allElements.forEach((element, index) => {
                    if (element) {
                        if (otasyncToggle.checked) {
                            element.style.display = 'block';
                            console.log(`✅ Showing element ${index + 1}:`, element.className);
                        } else {
                            element.style.display = 'none';
                            console.log(`❌ Hiding element ${index + 1}:`, element.className);
                        }
                    }
                });
                
                // Si se activa el toggle, cargar propiedades
                if (otasyncToggle.checked) {
                    loadOTASyncProperties();
                }
            }
            
            // Función para cargar propiedades OTASync dinámicamente
            async function loadOTASyncProperties() {
                const propertySelect = document.querySelector('select[data-otasync-select="true"]');
                if (!propertySelect) return;
                
                console.log('🔄 Loading OTASync properties...');
                propertySelect.innerHTML = '<option value="">Cargando propiedades...</option>';
                
                try {
                    const response = await fetch('/hotels/otasync-properties/');
                    if (!response.ok) throw new Error('Failed to fetch properties');
                    
                    const data = await response.json();
                    console.log('✅ Properties loaded:', data);
                    
                    propertySelect.innerHTML = '<option value="">Seleccionar propiedad...</option>';
                    
                    if (data.properties && data.properties.length > 0) {
                        data.properties.forEach(prop => {
                            const option = document.createElement('option');
                            option.value = prop.id;
                            option.textContent = `${prop.name} (ID: ${prop.id})`;
                            propertySelect.appendChild(option);
                        });
                        
                        // Actualizar el texto de ayuda
                        const helpText = propertySelect.nextElementSibling;
                        if (helpText && helpText.classList.contains('text-muted')) {
                            helpText.textContent = 'Selecciona la propiedad de OTASync registrada en tu cuenta.';
                        }
                        
                        console.log(`✅ ${data.properties.length} properties loaded successfully`);
                    } else {
                        propertySelect.innerHTML = '<option value="">No hay propiedades disponibles</option>';
                        console.log('⚠️ No properties found');
                    }
                } catch (error) {
                    console.error('❌ Error loading properties:', error);
                    propertySelect.innerHTML = '<option value="">Error cargando propiedades</option>';
                }
            }
            
            // Initial state
            toggleOTASyncFields();
            
            // Toggle on change
            otasyncToggle.addEventListener('change', function() {
                console.log('🎯 OTASync toggle changed to:', this.checked);
                toggleOTASyncFields();
            });
        }

        // Handle OTASync property selection
        const propertySelect = document.querySelector('select[name="otasync_property_id"]');
        const pricingPlanInput = document.querySelector('input[name="otasync_pricing_plan_id"]');
        
        console.log('🎯 Property select found:', !!propertySelect);
        console.log('🎯 Pricing plan input found:', !!pricingPlanInput);
        
        if (propertySelect && pricingPlanInput) {
            propertySelect.addEventListener('change', function() {
                console.log('🎯 Property selected:', this.value);
                const selectedOption = this.options[this.selectedIndex];
                
                if (selectedOption && selectedOption.value) {
                    // Auto-fill default pricing plan based on property
                    // For now, use the default value 26946, but this could be enhanced
                    // to get pricing plans from the API
                    if (!pricingPlanInput.value) {
                        pricingPlanInput.value = '26946';
                        console.log('✅ Auto-filled pricing plan: 26946');
                    }
                    
                    // Show visual feedback
                    pricingPlanInput.classList.add('border-success');
                    setTimeout(() => {
                        pricingPlanInput.classList.remove('border-success');
                    }, 1000);
                } else {
                    pricingPlanInput.value = '';
                    console.log('❌ Cleared pricing plan');
                }
            });
        }
        
        console.log('✅ Hotels JS: Initialization complete');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHotelsPage);
    } else {
        initHotelsPage();
    }
})();
