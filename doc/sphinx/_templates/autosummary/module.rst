{{ fullname | escape | underline }}

..
  Custom formatting of module doc layout
  https://stackoverflow.com/questions/48074094/use-sphinx-autosummary-recursively-to-generate-api-documentation
  TODO: how can we add the documented module attribuets (constants, ...)?

.. rubric:: Description

.. automodule:: {{ fullname }}

.. currentmodule:: {{ fullname }}


{% if classes %}
.. rubric:: Classes

.. autosummary::
    :toctree: .

    {% for item in classes %}
    {{ item }}
    {% endfor %}

{% endif %}


{% if functions %}
.. rubric:: Functions

.. autosummary::
    :toctree: .
    {% for item in functions %}
    {{ item }}
    {% endfor %}

{% endif %}


{% if exceptions %}
.. rubric:: Exceptions

.. autosummary::
    :toctree: .
    {% for item in exceptions %}
    {{ item }}
    {% endfor %}

{% endif %}
