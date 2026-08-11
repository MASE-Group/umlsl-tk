# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'zoom_buttons.ui'
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
from PySide6.QtWidgets import (QApplication, QSizePolicy, QToolButton, QVBoxLayout,
    QWidget)
from . import resources_rc

class Ui_Zoom_Buttons(object):
    def setupUi(self, Zoom_Buttons):
        if not Zoom_Buttons.objectName():
            Zoom_Buttons.setObjectName(u"Zoom_Buttons")
        Zoom_Buttons.resize(70, 96)
        Zoom_Buttons.setStyleSheet(u"QToolButton {\n"
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
"    background-color: #1A252E;\n"
"}")
        self.verticalLayout = QVBoxLayout(Zoom_Buttons)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolButton = QToolButton(Zoom_Buttons)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMinimumSize(QSize(32, 32))
        self.toolButton.setMaximumSize(QSize(32, 32))
        icon = QIcon()
        icon.addFile(u":/icons/icons/add.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon)

        self.verticalLayout.addWidget(self.toolButton)

        self.toolButton_2 = QToolButton(Zoom_Buttons)
        self.toolButton_2.setObjectName(u"toolButton_2")
        self.toolButton_2.setMinimumSize(QSize(32, 32))
        self.toolButton_2.setMaximumSize(QSize(32, 32))
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/remove.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton_2.setIcon(icon1)

        self.verticalLayout.addWidget(self.toolButton_2)


        self.retranslateUi(Zoom_Buttons)

        QMetaObject.connectSlotsByName(Zoom_Buttons)
    # setupUi

    def retranslateUi(self, Zoom_Buttons):
        Zoom_Buttons.setWindowTitle(QCoreApplication.translate("Zoom_Buttons", u"Form", None))
        self.toolButton.setText("")
        self.toolButton_2.setText("")
    # retranslateUi

