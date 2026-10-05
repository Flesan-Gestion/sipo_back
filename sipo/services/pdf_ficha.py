"""Generación PDF Anexo 02 — Ficha de Ingreso de Personal (P-RH-01)."""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from sipo.models_ficha import SipoFichaIngreso
from sipo.services.ficha_labels import resolve_catalog_label


def _txt(value) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _fmt_date(value) -> str:
    if not value:
        return ''
    if isinstance(value, date):
        return value.strftime('%d-%m-%Y')
    return str(value)[:10]


def _fmt_money(value) -> str:
    if value is None:
        return ''
    try:
        return f'$ {int(value):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return str(value)


def _cell(label: str, value: str, styles) -> list:
    return [
        Paragraph(f'<b>{label}</b>', styles['label']),
        Paragraph(_txt(value) or '—', styles['value']),
    ]


def build_ficha_pdf(ficha: SipoFichaIngreso) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=f'Ficha Ingreso {_txt(ficha.rut)}',
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name='DocTitle',
            parent=styles['Heading1'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=10,
            textColor=colors.HexColor('#252527'),
        )
    )
    styles.add(
        ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontSize=9,
            textColor=colors.HexColor('#252527'),
            spaceBefore=8,
            spaceAfter=4,
            borderPadding=2,
        )
    )
    styles.add(
        ParagraphStyle(name='label', fontSize=7, textColor=colors.HexColor('#4b5563'), leading=9)
    )
    styles.add(
        ParagraphStyle(name='value', fontSize=8, textColor=colors.HexColor('#111827'), leading=10)
    )
    styles.add(
        ParagraphStyle(name='meta', fontSize=8, alignment=TA_RIGHT, leading=11)
    )
    styles.add(
        ParagraphStyle(name='firma', fontSize=8, alignment=TA_CENTER, spaceBefore=28)
    )

    story = []

    header = Table(
        [
            [
                Paragraph(
                    '<b>FLESAN</b> · DVC · InexChile · FAI<br/>'
                    '<font size="7">Grupo Flesan</font>',
                    styles['value'],
                ),
                Paragraph(
                    '<b>Cód:</b> P-RH-01<br/><b>Anexo:</b> 02',
                    styles['meta'],
                ),
            ]
        ],
        colWidths=[11 * cm, 7 * cm],
    )
    header.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 8))
    story.append(Paragraph('Ficha de Ingreso de Personal', styles['DocTitle']))

    def section_table(title: str, rows: list[list]):
        story.append(Paragraph(title.upper(), styles['SectionTitle']))
        data = []
        for pair in rows:
            if len(pair) == 2:
                data.append([pair[0][0], pair[0][1], pair[1][0], pair[1][1]])
            else:
                data.append([pair[0][0], pair[0][1], '', ''])
        table = Table(data, colWidths=[3.2 * cm, 5.8 * cm, 3.2 * cm, 5.8 * cm])
        table.setStyle(
            TableStyle(
                [
                    ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d1d5db')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f9fafb')),
                    ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f9fafb')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('SPAN', (1, len(data) - 1), (3, len(data) - 1))
                    if False
                    else ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]
            )
        )
        story.append(table)

    section_table(
        '1. Datos a completar por Recursos Humanos y Área Solicitante',
        [
            [
                _cell('Razón Social', ficha.razon_social_nombre or ficha.razon_social_id, styles),
                _cell('Obra', ficha.obra, styles),
            ],
            [
                _cell('Centro de Costo', ficha.centro_costo_id, styles),
                _cell('Descripción CC', ficha.centro_costo_nombre, styles),
            ],
            [
                _cell('Cargo', ficha.cargo, styles),
                _cell('Fecha ingreso', _fmt_date(ficha.fecha_ingreso), styles),
            ],
            [
                _cell('Correo Jefe Directo', ficha.correo_jefe_directo, styles),
                _cell('Correo Admin. Obra', ficha.correo_admin_obra, styles),
            ],
        ],
    )

    section_table(
        '2. Datos a completar por Nuevo Colaborador',
        [
            [
                _cell('Nombres', ficha.nombres, styles),
                _cell('Primer Apellido', ficha.apellido_paterno, styles),
            ],
            [
                _cell('Segundo Apellido', ficha.apellido_materno, styles),
                _cell('RUT', ficha.rut, styles),
            ],
            [
                _cell('AFP', resolve_catalog_label('afp', ficha.afp), styles),
                _cell(
                    'Isapre / Fonasa',
                    resolve_catalog_label('isapre_fonasa', ficha.isapre_fonasa),
                    styles,
                ),
            ],
            [
                _cell('Jubilado', 'Sí' if ficha.jubilado else 'No', styles),
                _cell(
                    'Estado Civil',
                    resolve_catalog_label('estado_civil', ficha.estado_civil),
                    styles,
                ),
            ],
            [
                _cell('Edad', ficha.edad, styles),
                _cell('Fecha Nacimiento', _fmt_date(ficha.fecha_nacimiento), styles),
            ],
            [
                _cell('Teléfono', ficha.telefono, styles),
                _cell('Domicilio', ficha.domicilio, styles),
            ],
            [
                _cell('Comuna', ficha.comuna, styles),
                _cell('Ciudad', ficha.ciudad, styles),
            ],
            [
                _cell('Región', ficha.region, styles),
                _cell('E-mail Personal', ficha.email_personal, styles),
            ],
            [
                _cell('Banco', resolve_catalog_label('banco', ficha.banco), styles),
                _cell('Método de Pago', ficha.metodo_pago, styles),
            ],
            [
                _cell('N° Cuenta', ficha.numero_cuenta, styles),
                _cell('Villa', ficha.villa, styles),
            ],
            [
                _cell('N° Dirección', ficha.numero_direccion, styles),
                _cell('N° Depto', ficha.num_depto, styles),
            ],
            [
                _cell('Tratamiento', ficha.tratamiento, styles),
                _cell('Género', ficha.genero, styles),
            ],
            [
                _cell('Nacionalidad', ficha.nacionalidad, styles),
                _cell('', '', styles),
            ],
            *(
                [
                    [
                        _cell('Nacionalidad extranjera', ficha.nacionalidad_ext, styles),
                        _cell('', '', styles),
                    ]
                ]
                if (ficha.nacionalidad or '') in ('Extranjero', 'Extranjero-Definitiva')
                else []
            ),
            [
                _cell('País Nacimiento', ficha.pais_nacimiento, styles),
                _cell('Región Nacimiento', ficha.region_nacimiento, styles),
            ],
        ],
    )

    docs = []
    if ficha.doc_domicilio:
        docs.append('Comprobante de Domicilio')
    if ficha.doc_titulo:
        docs.append('Certificado de Título')
    if ficha.doc_afp:
        docs.append('Certificado AFP')
    if ficha.doc_salud:
        docs.append('Certificado Salud')
    if ficha.doc_cedula:
        docs.append('Cédula de Identidad')

    contrata_rows = [
        [
            _cell('Sueldo Líquido', _fmt_money(ficha.sueldo_liquido), styles),
            _cell('Cuenta Gasto', ficha.cuenta_gasto, styles),
        ],
        [
            _cell('Tipo Contrato', ficha.tipo_contrato, styles),
            _cell(
                'HITO' if (ficha.tipo_contrato or '') == 'Obra o Faena' else 'Término Contrato',
                ficha.termino_contrato,
                styles,
            ),
        ],
    ]
    if (ficha.tipo_contrato or '') == 'Obra o Faena':
        contrata_rows.append(
            [
                _cell('Días Contrato', ficha.dias_contrato, styles),
                _cell(
                    'Fecha Término HITO',
                    _fmt_date(ficha.fecha_termino_ito),
                    styles,
                ),
            ]
        )
        contrata_rows.append(
            [
                _cell('Horario', resolve_catalog_label('horario', ficha.horario), styles),
                _cell('Documentos', ', '.join(docs) if docs else 'Sin adjuntos', styles),
            ]
        )
    else:
        contrata_rows.append(
            [
                _cell('Días Contrato', ficha.dias_contrato, styles),
                _cell('Horario', resolve_catalog_label('horario', ficha.horario), styles),
            ]
        )
        contrata_rows.append(
            [
                _cell('Documentos', ', '.join(docs) if docs else 'Sin adjuntos', styles),
            ]
        )
    contrata_rows.append(
        [
            _cell('Observaciones', ficha.observaciones, styles),
        ]
    )

    section_table(
        '3. Datos de Contratación y Documentos',
        contrata_rows,
    )

    story.append(Spacer(1, 18))
    firmas = Table(
        [
            [
                Paragraph('__________________________<br/><b>V° B° Jefe Directo</b>', styles['firma']),
                Paragraph(
                    '__________________________<br/><b>V° B° Administrador de Obra</b>',
                    styles['firma'],
                ),
                Paragraph('__________________________<br/><b>V° B° Recursos Humanos</b>', styles['firma']),
            ]
        ],
        colWidths=[6 * cm, 6 * cm, 6 * cm],
    )
    story.append(firmas)

    doc.build(story)
    return buffer.getvalue()
