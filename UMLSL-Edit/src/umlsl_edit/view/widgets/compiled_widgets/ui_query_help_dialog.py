# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'query_help_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout,
    QLabel, QLayout, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)
from . import resources_rc

class Ui_QueryHelpDialog(object):
    def setupUi(self, QueryHelpDialog):
        if not QueryHelpDialog.objectName():
            QueryHelpDialog.setObjectName(u"QueryHelpDialog")
        QueryHelpDialog.resize(359, 644)
        QueryHelpDialog.setMinimumSize(QSize(0, 0))
        QueryHelpDialog.setMaximumSize(QSize(16777215, 16777215))
        QueryHelpDialog.setStyleSheet(u"QDialog {\n"
"    background-color: #011C26; \n"
"}\n"
"\n"
"QWidget {	\n"
"	font: 13pt \"Helvetica\";\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QLabel[class=label] {	\n"
"	font: 10pt;\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QWidget[class=container] {	\n"
"    background: #042F40;\n"
"	border-radius: 10px;\n"
"}\n"
"\n"
"QLabel[class=hint] {\n"
"	color: #799582;\n"
"}\n"
"\n"
"QLabel[class=title] {\n"
"	font: 700 24pt;\n"
"}\n"
"\n"
"QLineEdit{\n"
"	background-color: #011C26;\n"
"	border: none;\n"
"	border-radius: 6px;\n"
"	\n"
"}\n"
"\n"
"/* --- Main Box --- */\n"
"QComboBox {\n"
"    background-color: #011C26;\n"
"    border: none;\n"
"    border-radius: 6px;\n"
"    padding: 5px 10px;\n"
"    color: #F9F9F9;\n"
"    /* This helps selection color in some styles */\n"
"    selection-background-color: #011C26; \n"
"}\n"
"\n"
"/* --- The Dropdown Frame --- */\n"
"/* We target QListView specifically to override Mac defaults */\n"
"QComboBox QListView {\n"
"    background-color: #011C26;\n"
"    border: 1px solid #04"
                        "2F40; /* Your custom border */\n"
"    outline: 0px; /* Removes the dotted/blue focus line */\n"
"    padding: 0px;\n"
"}\n"
"\n"
"\n"
"\n"
"/* --- The Arrow Button Area --- */\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 24px;\n"
"    border-left: 1px solid #042F40; /* Optional: adds a separator */\n"
"    border-top-right-radius: 6px;\n"
"    border-bottom-right-radius: 6px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    image: url(:/icons/icons/down.svg);\n"
"    width: 10px;\n"
"    height: 10px;\n"
"}\n"
"\n"
"/* --- Main Spinbox Styling (Applies to both) --- */\n"
"QSpinBox, QDoubleSpinBox {\n"
"    background-color: #011C26;\n"
"    border: none;\n"
"    border-radius: 6px;\n"
"    color: #F9F9F9;\n"
"    padding: 5px 10px;\n"
"    padding-right: 15px; \n"
"}\n"
"\n"
"/* --- The Button Container Areas --- */\n"
"QSpinBox::up-button, QDoubleSpinBox::up-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top righ"
                        "t;\n"
"    width: 25px;\n"
"    \n"
"    border-left: 1px solid #042F40;\n"
"    border-top-right-radius: 6px;\n"
"    border-bottom: 1px solid #042F40;\n"
"    \n"
"    background-color: #011C26;\n"
"}\n"
"\n"
"QSpinBox::down-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: bottom right;\n"
"    width: 25px;\n"
"    \n"
"    border-left: 1px solid #042F40;\n"
"    border-bottom-right-radius: 6px;\n"
"    \n"
"    background-color: #011C26;\n"
"}\n"
"\n"
"/* --- Hover Effects --- */\n"
"QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,\n"
"QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QComboBox::drop-down:hover {\n"
"    background-color: #042F40;\n"
"}\n"
"\n"
"/* --- The Arrow Icons --- */\n"
"/* (Assuming you are using the CSS Arrow hack from before. \n"
"   If using images, replace these with your image: url(...) code) */\n"
"\n"
"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {\n"
"    image: url(:/icons/icons/up.svg); /* You n"
                        "eed to create this file */\n"
"    width: 10px;\n"
"    height: 10px;\n"
"}\n"
"\n"
"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {\n"
"    image: url(:/icons/icons/down.svg); /* You need to create this file */\n"
"    width: 10px;\n"
"    height: 10px;\n"
"}\n"
"\n"
"QToolButton {\n"
"    background-color: #032F40; \n"
"    border-radius: 16px;       \n"
"    border: none;\n"
"    text-align: center;\n"
"}\n"
"\n"
"QToolButton:hover {\n"
"    background-color: #314250; \n"
"}\n"
"\n"
"QToolButton:pressed {\n"
"    background-color: #032F40;\n"
"}\n"
"\n"
"QPushButton {\n"
"	color: #011C26;\n"
"	border-radius: 16px;\n"
"}\n"
"\n"
"QPushButton#b_close {\n"
"	background-color: #042F40;\n"
"	color: #F9F9F9\n"
"}\n"
"\n"
"QPushButton#b_close:hover {\n"
"    background-color: #314250; \n"
"}\n"
"QPushButton#b_close:pressed {\n"
"    background-color: #042F40; \n"
"}")
        self.verticalLayout = QVBoxLayout(QueryHelpDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.widget = QWidget(QueryHelpDialog)
        self.widget.setObjectName(u"widget")
        self.Lanes = QVBoxLayout(self.widget)
        self.Lanes.setSpacing(0)
        self.Lanes.setObjectName(u"Lanes")
        self.Lanes.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.Lanes.setContentsMargins(0, 0, 0, 0)
        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        self.widget_3.setMinimumSize(QSize(0, 500))
        self.gridLayout = QGridLayout(self.widget_3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_11 = QLabel(self.widget_3)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setMinimumSize(QSize(0, 13))
        self.label_11.setMaximumSize(QSize(16777215, 16777215))
        self.label_11.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_11, 0, 0, 1, 1)

        self.label_6 = QLabel(self.widget_3)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setMinimumSize(QSize(0, 0))
        self.label_6.setMaximumSize(QSize(16777215, 16777215))
        self.label_6.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_6, 0, 1, 1, 2)

        self.label_13 = QLabel(self.widget_3)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setMinimumSize(QSize(0, 13))
        self.label_13.setMaximumSize(QSize(16777215, 16777215))
        self.label_13.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_13, 1, 0, 1, 1)

        self.label_8 = QLabel(self.widget_3)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setMinimumSize(QSize(0, 0))
        self.label_8.setMaximumSize(QSize(16777215, 16777215))
        self.label_8.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_8, 1, 1, 1, 1)

        self.label_12 = QLabel(self.widget_3)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setMinimumSize(QSize(0, 13))
        self.label_12.setMaximumSize(QSize(16777215, 16777215))
        self.label_12.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_12, 2, 0, 1, 1)

        self.label_7 = QLabel(self.widget_3)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setMinimumSize(QSize(0, 0))
        self.label_7.setMaximumSize(QSize(16777215, 16777215))
        self.label_7.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_7, 2, 1, 1, 2)

        self.label_15 = QLabel(self.widget_3)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setMinimumSize(QSize(0, 13))
        self.label_15.setMaximumSize(QSize(16777215, 16777215))
        self.label_15.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_15, 3, 0, 1, 1)

        self.label_9 = QLabel(self.widget_3)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setMinimumSize(QSize(0, 0))
        self.label_9.setMaximumSize(QSize(16777215, 16777215))
        self.label_9.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_9, 3, 1, 1, 2)

        self.label_16 = QLabel(self.widget_3)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setMinimumSize(QSize(0, 13))
        self.label_16.setMaximumSize(QSize(16777215, 16777215))
        self.label_16.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_16, 4, 0, 1, 1)

        self.label_17 = QLabel(self.widget_3)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setMinimumSize(QSize(0, 0))
        self.label_17.setMaximumSize(QSize(16777215, 16777215))
        self.label_17.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_17, 4, 1, 1, 2)

        self.label_25 = QLabel(self.widget_3)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setMinimumSize(QSize(0, 13))
        self.label_25.setMaximumSize(QSize(16777215, 16777215))
        self.label_25.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_25, 5, 0, 1, 1)

        self.label_29 = QLabel(self.widget_3)
        self.label_29.setObjectName(u"label_29")
        self.label_29.setMinimumSize(QSize(0, 0))
        self.label_29.setMaximumSize(QSize(16777215, 16777215))
        self.label_29.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_29, 5, 1, 1, 2)

        self.label_21 = QLabel(self.widget_3)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setMinimumSize(QSize(0, 13))
        self.label_21.setMaximumSize(QSize(16777215, 16777215))
        self.label_21.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_21, 6, 0, 1, 1)

        self.label_18 = QLabel(self.widget_3)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setMinimumSize(QSize(0, 13))
        self.label_18.setMaximumSize(QSize(16777215, 16777215))
        self.label_18.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_18, 7, 0, 1, 1)

        self.label_24 = QLabel(self.widget_3)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setMinimumSize(QSize(0, 0))
        self.label_24.setMaximumSize(QSize(16777215, 16777215))
        self.label_24.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_24, 7, 1, 1, 1)

        self.label_23 = QLabel(self.widget_3)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setMinimumSize(QSize(0, 13))
        self.label_23.setMaximumSize(QSize(16777215, 16777215))
        self.label_23.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_23, 8, 0, 1, 1)

        self.label_26 = QLabel(self.widget_3)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setMinimumSize(QSize(0, 0))
        self.label_26.setMaximumSize(QSize(16777215, 16777215))
        self.label_26.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_26, 8, 1, 1, 1)

        self.label_28 = QLabel(self.widget_3)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setMinimumSize(QSize(0, 13))
        self.label_28.setMaximumSize(QSize(16777215, 16777215))
        self.label_28.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_28, 9, 0, 1, 1)

        self.label_22 = QLabel(self.widget_3)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setMinimumSize(QSize(0, 0))
        self.label_22.setMaximumSize(QSize(16777215, 16777215))
        self.label_22.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_22, 9, 1, 1, 1)

        self.label_32 = QLabel(self.widget_3)
        self.label_32.setObjectName(u"label_32")
        self.label_32.setMinimumSize(QSize(0, 13))
        self.label_32.setMaximumSize(QSize(16777215, 16777215))
        self.label_32.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_32, 10, 0, 1, 1)

        self.label_34 = QLabel(self.widget_3)
        self.label_34.setObjectName(u"label_34")
        self.label_34.setMinimumSize(QSize(0, 0))
        self.label_34.setMaximumSize(QSize(16777215, 16777215))
        self.label_34.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_34, 10, 1, 1, 1)

        self.label_35 = QLabel(self.widget_3)
        self.label_35.setObjectName(u"label_35")
        self.label_35.setMinimumSize(QSize(0, 13))
        self.label_35.setMaximumSize(QSize(16777215, 16777215))
        self.label_35.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_35, 11, 0, 1, 1)

        self.label_36 = QLabel(self.widget_3)
        self.label_36.setObjectName(u"label_36")
        self.label_36.setMinimumSize(QSize(0, 0))
        self.label_36.setMaximumSize(QSize(16777215, 16777215))
        self.label_36.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_36, 11, 1, 1, 2)

        self.label_38 = QLabel(self.widget_3)
        self.label_38.setObjectName(u"label_38")
        self.label_38.setMinimumSize(QSize(0, 13))
        self.label_38.setMaximumSize(QSize(16777215, 16777215))
        self.label_38.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_38, 12, 0, 1, 1)

        self.label_37 = QLabel(self.widget_3)
        self.label_37.setObjectName(u"label_37")
        self.label_37.setMinimumSize(QSize(0, 0))
        self.label_37.setMaximumSize(QSize(16777215, 16777215))
        self.label_37.setTextFormat(Qt.TextFormat.MarkdownText)
        self.label_37.setWordWrap(True)

        self.gridLayout.addWidget(self.label_37, 12, 1, 1, 2)

        self.label_19 = QLabel(self.widget_3)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setMinimumSize(QSize(0, 13))
        self.label_19.setMaximumSize(QSize(16777215, 16777215))
        self.label_19.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_19, 13, 0, 1, 1)

        self.label_20 = QLabel(self.widget_3)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setMinimumSize(QSize(0, 0))
        self.label_20.setMaximumSize(QSize(16777215, 16777215))
        self.label_20.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_20, 13, 1, 1, 2)

        self.label_31 = QLabel(self.widget_3)
        self.label_31.setObjectName(u"label_31")
        self.label_31.setMinimumSize(QSize(0, 13))
        self.label_31.setMaximumSize(QSize(16777215, 16777215))
        self.label_31.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_31, 14, 0, 1, 1)

        self.label_33 = QLabel(self.widget_3)
        self.label_33.setObjectName(u"label_33")
        self.label_33.setMinimumSize(QSize(0, 0))
        self.label_33.setMaximumSize(QSize(16777215, 16777215))
        self.label_33.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout.addWidget(self.label_33, 14, 1, 1, 2)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_27 = QLabel(self.widget_3)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setMinimumSize(QSize(0, 0))
        self.label_27.setMaximumSize(QSize(16777215, 16777215))
        self.label_27.setTextFormat(Qt.TextFormat.MarkdownText)

        self.verticalLayout_2.addWidget(self.label_27)

        self.label_39 = QLabel(self.widget_3)
        self.label_39.setObjectName(u"label_39")
        self.label_39.setMinimumSize(QSize(0, 0))
        self.label_39.setMaximumSize(QSize(16777215, 16777215))
        self.label_39.setTextFormat(Qt.TextFormat.MarkdownText)

        self.verticalLayout_2.addWidget(self.label_39)

        self.label_30 = QLabel(self.widget_3)
        self.label_30.setObjectName(u"label_30")
        self.label_30.setMinimumSize(QSize(0, 0))
        self.label_30.setMaximumSize(QSize(16777215, 16777215))

        self.verticalLayout_2.addWidget(self.label_30)


        self.gridLayout.addLayout(self.verticalLayout_2, 6, 1, 1, 1)


        self.Lanes.addWidget(self.widget_3)


        self.verticalLayout.addWidget(self.widget)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 8, -1, -1)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.b_close = QPushButton(QueryHelpDialog)
        self.b_close.setObjectName(u"b_close")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.b_close.sizePolicy().hasHeightForWidth())
        self.b_close.setSizePolicy(sizePolicy)
        self.b_close.setMinimumSize(QSize(141, 32))
        self.b_close.setMaximumSize(QSize(141, 32))
        icon = QIcon()
        icon.addFile(u":/icons/icons/cancel.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_close.setIcon(icon)

        self.horizontalLayout.addWidget(self.b_close)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(QueryHelpDialog)
        self.b_close.clicked.connect(QueryHelpDialog.accept)

        QMetaObject.connectSlotsByName(QueryHelpDialog)
    # setupUi

    def retranslateUi(self, QueryHelpDialog):
        QueryHelpDialog.setWindowTitle(QCoreApplication.translate("QueryHelpDialog", u"Help Query Syntax", None))
        self.widget_3.setProperty(u"class", "")
        self.label_11.setText(QCoreApplication.translate("QueryHelpDialog", u"cs", None))
        self.label_6.setText(QCoreApplication.translate("QueryHelpDialog", u"Crossing Segment", None))
        self.label_13.setText(QCoreApplication.translate("QueryHelpDialog", u"free", None))
        self.label_8.setText(QCoreApplication.translate("QueryHelpDialog", u"No Car", None))
        self.label_12.setText(QCoreApplication.translate("QueryHelpDialog", u"<\U0001d719>", None))
        self.label_7.setText(QCoreApplication.translate("QueryHelpDialog", u"Somewhere", None))
        self.label_15.setText(QCoreApplication.translate("QueryHelpDialog", u"re{c}", None))
        self.label_9.setText(QCoreApplication.translate("QueryHelpDialog", u"Reserved Space", None))
        self.label_16.setText(QCoreApplication.translate("QueryHelpDialog", u"cl{c}", None))
        self.label_17.setText(QCoreApplication.translate("QueryHelpDialog", u"Claimed Space", None))
        self.label_25.setText(QCoreApplication.translate("QueryHelpDialog", u"hchop {\U0001d7191} ... {\U0001d719n}", None))
        self.label_29.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 \U00002322 ... \U00002322 \U0001d719n", None))
        self.label_21.setText(QCoreApplication.translate("QueryHelpDialog", u"vchop {\U0001d7191} ... {\U0001d719n}", None))
        self.label_18.setText(QCoreApplication.translate("QueryHelpDialog", u"neg \U0001d719, !\U0001d719", None))
        self.label_24.setText(QCoreApplication.translate("QueryHelpDialog", u"\U000000ac \U0001d719", None))
        self.label_23.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 and \U0001d7192", None))
        self.label_26.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 \U00002227 \U0001d7192", None))
        self.label_28.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 or \U0001d7192", None))
        self.label_22.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 \U00002228 \U0001d7192", None))
        self.label_32.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 => \U0001d7192", None))
        self.label_34.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191 \U000027f9 \U0001d7192", None))
        self.label_35.setText(QCoreApplication.translate("QueryHelpDialog", u"a = b, a != b", None))
        self.label_36.setText(QCoreApplication.translate("QueryHelpDialog", u"Car a (not) equals Car b", None))
        self.label_38.setText(QCoreApplication.translate("QueryHelpDialog", u"l {<, <= , >= ,>} v", None))
        self.label_37.setText(QCoreApplication.translate("QueryHelpDialog", u"Compares length of horizon with number v", None))
        self.label_19.setText(QCoreApplication.translate("QueryHelpDialog", u"forall c: \U0001d719", None))
        self.label_20.setText(QCoreApplication.translate("QueryHelpDialog", u"\u2200 / For All Cars c", None))
        self.label_31.setText(QCoreApplication.translate("QueryHelpDialog", u"exists c: \U0001d719", None))
        self.label_33.setText(QCoreApplication.translate("QueryHelpDialog", u"\u2203 / Exists Car c", None))
        self.label_27.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d7191", None))
        self.label_39.setText(QCoreApplication.translate("QueryHelpDialog", u"...", None))
        self.label_30.setText(QCoreApplication.translate("QueryHelpDialog", u"\U0001d719n", None))
        self.b_close.setText(QCoreApplication.translate("QueryHelpDialog", u"Close", None))
    # retranslateUi

