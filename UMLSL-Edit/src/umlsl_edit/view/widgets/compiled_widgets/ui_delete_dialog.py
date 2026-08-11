# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'delete_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QLayout, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)
from . import resources_rc

class Ui_Delete_Dialog(object):
    def setupUi(self, Delete_Dialog):
        if not Delete_Dialog.objectName():
            Delete_Dialog.setObjectName(u"Delete_Dialog")
        Delete_Dialog.resize(324, 118)
        Delete_Dialog.setMinimumSize(QSize(0, 0))
        Delete_Dialog.setMaximumSize(QSize(16777215, 16777215))
        Delete_Dialog.setStyleSheet(u"QDialog {\n"
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
"QPushButton#b_cancel {\n"
"	background-color: #042F40;\n"
"	color: #F9F9F9\n"
"}\n"
"\n"
"QPushButton#b_cancel:hover {\n"
"    background-color: #314250; \n"
"}\n"
"QPushButton#b_cancel:pressed {\n"
"    background-color: #042F40; \n"
"}\n"
"\n"
"QPushButton#b_delete {\n"
"	background-color: #D97855\n"
"}\n"
"\n"
"QPushButton#b_delete:hover {\n"
"    background-color: rgb(244, 13"
                        "5, 96); \n"
"}\n"
"QPushButton#b_delete:pressed {\n"
"    background-color: #D97855; \n"
"}")
        self.verticalLayout = QVBoxLayout(Delete_Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.l_title = QLabel(Delete_Dialog)
        self.l_title.setObjectName(u"l_title")

        self.verticalLayout.addWidget(self.l_title)

        self.l_content = QLabel(Delete_Dialog)
        self.l_content.setObjectName(u"l_content")
        self.l_content.setMinimumSize(QSize(300, 0))
        self.l_content.setMaximumSize(QSize(300, 16777215))

        self.verticalLayout.addWidget(self.l_content)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 8, -1, -1)
        self.b_delete = QPushButton(Delete_Dialog)
        self.b_delete.setObjectName(u"b_delete")
        self.b_delete.setMinimumSize(QSize(32, 32))
        self.b_delete.setMaximumSize(QSize(16777215, 32))
        icon = QIcon()
        icon.addFile(u":/icons/icons/delete_dark.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_delete.setIcon(icon)

        self.horizontalLayout.addWidget(self.b_delete)

        self.b_cancel = QPushButton(Delete_Dialog)
        self.b_cancel.setObjectName(u"b_cancel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.b_cancel.sizePolicy().hasHeightForWidth())
        self.b_cancel.setSizePolicy(sizePolicy)
        self.b_cancel.setMinimumSize(QSize(32, 32))
        self.b_cancel.setMaximumSize(QSize(16777215, 32))
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/cancel.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_cancel.setIcon(icon1)

        self.horizontalLayout.addWidget(self.b_cancel)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(Delete_Dialog)
        self.b_delete.clicked.connect(Delete_Dialog.accept)
        self.b_cancel.clicked.connect(Delete_Dialog.reject)

        QMetaObject.connectSlotsByName(Delete_Dialog)
    # setupUi

    def retranslateUi(self, Delete_Dialog):
        Delete_Dialog.setWindowTitle(QCoreApplication.translate("Delete_Dialog", u"Confirm Action", None))
        self.l_title.setText(QCoreApplication.translate("Delete_Dialog", u"Are you sure?", None))
        self.l_title.setProperty(u"class", QCoreApplication.translate("Delete_Dialog", u"title", None))
        self.l_content.setText(QCoreApplication.translate("Delete_Dialog", u"This Action can not be undone.", None))
        self.b_delete.setText(QCoreApplication.translate("Delete_Dialog", u"Delete", None))
        self.b_cancel.setText(QCoreApplication.translate("Delete_Dialog", u"Cancel", None))
    # retranslateUi

