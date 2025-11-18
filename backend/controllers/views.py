from flask import Blueprint, render_template, redirect, url_for

views_bp = Blueprint("views", __name__)


@views_bp.get("/")
def home():
    """
    Página inicial: redireciona para a página de sensores.
    Se preferir outra página inicial, troque 'views.sensores' por 'views.atuadores' ou 'views.alertas'.
    """
    return redirect(url_for("views.sensores"))


@views_bp.get("/sensores")
def sensores():
    """
    Página de cadastro e visualização de sensores.
    Arquivo de template: frontend/templates/sensores.html
    """
    return render_template("sensores.html")


@views_bp.get("/atuadores")
def atuadores():
    """
    Página de cadastro e visualização de atuadores.
    Arquivo de template: frontend/templates/atuadores.html
    """
    return render_template("atuadores.html")


@views_bp.get("/alertas")
def alertas():
    """
    Página de visualização de alertas e leituras simuladas.
    Arquivo de template: frontend/templates/alertas.html
    """
    return render_template("alertas.html")
