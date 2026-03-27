# Import all forms for easy access
from app.forms.auth_forms import RegisterForm, LoginForm
from app.forms.incident_forms import IncidentForm, StatusUpdateForm
from app.forms.equipment_forms import EquipmentForm, EquipmentCheckoutForm, EquipmentReturnForm
from app.forms.communication_forms import MessageForm, RadioLogForm, TemplateForm
from app.forms.volunteer_forms import VolunteerApplicationForm, ApplicationReviewForm, TrainingForm