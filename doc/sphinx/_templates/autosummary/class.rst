{{ fullname | escape | underline}}


.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
    :undoc-members:
    :show-inheritance:

   {% block attributes %}
   {% if attributes %}
      .. autosummary::
         :toctree:
      {% for item in all_attributes %}
         {%- if not item.startswith('_') %}
         {{ name }}.{{ item }}
         {%- endif -%}
      {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block methods %}
   {% if methods %}
      .. autosummary::
         :toctree:
      {% for item in all_methods %}
         {%- if not item.startswith('_') or item in ['__call__'] %}
         {{ name }}.{{ item }}
         {%- endif -%}
      {%- endfor %}
   {% endif %}
   {% endblock %}
