# Add to your routes
@bp.route('/manage_providers', methods=['GET', 'POST'])
@login_required  # Add authentication if needed
def manage_providers():
    """
    Allow admins to add/edit LLM providers
    """
    providers = db.session.query(Provider).order_by(Provider.provider_name).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            provider_name = request.form.get('provider_name')
            module_name = request.form.get('module_name')
            display_name = request.form.get('display_name')
            description = request.form.get('description')
            config = {
                'api_key': request.form.get('api_key')
                # Add other config options as needed
            }
            
            new_provider = Provider(
                provider_name=provider_name,
                module_name=module_name,
                display_name=display_name,
                description=description,
                config_json=json.dumps(config),
                enabled=True
            )
            
            db.session.add(new_provider)
            db.session.commit()
            flash(f"Provider '{display_name}' added successfully.", 'success')
            
        elif action == 'edit':
            provider_id = request.form.get('provider_id')
            provider = db.session.query(Provider).get(provider_id)
            
            if provider:
                provider.display_name = request.form.get('display_name')
                provider.description = request.form.get('description')
                provider.enabled = 'enabled' in request.form
                
                # Update API key only if provided
                new_api_key = request.form.get('api_key')
                if new_api_key:
                    config = json.loads(provider.config_json) if provider.config_json else {}
                    config['api_key'] = new_api_key
                    provider.config_json = json.dumps(config)
                
                db.session.commit()
                flash(f"Provider '{provider.display_name}' updated successfully.", 'success')
        
        return redirect(url_for('main.manage_providers'))
    
    return render_template('manage_providers.html', providers=providers)