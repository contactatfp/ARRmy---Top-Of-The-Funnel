from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Event, Invitation, Contact, InvitationStatus, db
from app.forms import InvitationForm

invitations_blueprint = Blueprint('invitation', __name__, template_folder='templates')


@invitations_blueprint.route('/invitation/create/<event_id>', methods=['GET', 'POST'])
def create_invitation(event_id):
    form = InvitationForm()

    # Fetch the event
    event = Event.query.get_or_404(event_id)

    # Get the list of contact IDs from the URL parameters or another source
    contact_ids = request.args.getlist('contact_id')

    # Fetch the contacts
    contacts = Contact.query.filter(Contact.Id.in_(contact_ids)).all()
    form.contact_id.choices = [(contact.Id, contact.Name) for contact in contacts]

    if form.validate_on_submit():
        invitation = Invitation(event_id=form.event_id.data,
                                contact_id=form.contact_id.data,
                                account_id=form.account_id.data,
                                contact_title=form.contact_title.data,
                                status=InvitationStatus[form.status.data])
        db.session.add(invitation)
        db.session.commit()
        flash('Invitation(s) created successfully', 'success')
        return redirect(url_for('invitation_list'))

    return render_template('create_invitation.html', title='Create Invitation', form=form, contacts=contacts,
                           event=event)


@invitations_blueprint.route('/send_invitations', methods=['POST'])
def send_invitations():
    data = request.json
    selected_contacts = data.get('selected_contacts', [])

    # Your logic to send invitations
    # This could be storing the IDs in a database, sending emails, etc.

    return jsonify({"status": "success"})


@invitations_blueprint.route('/save_invitations', methods=['POST'])
def save_invitations():
    data = request.json
    selected_contacts = data.get('selected_contacts', [])
    event_id = data.get('event_id')

    for contact_id in selected_contacts:
        invitation = Invitation(contact_id=contact_id, event_id=event_id)
        db.session.add(invitation)
    db.session.commit()

    return jsonify({"status": "success"})
