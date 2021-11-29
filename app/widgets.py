from flask_appbuilder.widgets import FormWidget, ListWidget, ShowWidget

class Web3FormWidget(FormWidget):
    template = 'widgets/add_form.html'

class Web3ListWidget(ListWidget):
    template = 'widgets/list_form.html'

class Web3ShowWidget(ShowWidget):
    template = 'widgets/show_form.html'
