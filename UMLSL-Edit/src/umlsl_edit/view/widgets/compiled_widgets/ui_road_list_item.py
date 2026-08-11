# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'road_list_item.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QSizePolicy,
    QSpacerItem, QToolButton, QWidget)
from . import resources_rc

class Ui_Road_List_Item(object):
    def setupUi(self, Road_List_Item):
        if not Road_List_Item.objectName():
            Road_List_Item.setObjectName(u"Road_List_Item")
        Road_List_Item.resize(506, 56)
        Road_List_Item.setStyleSheet(u"QWidget{\n"
"	background-color: #011C26;\n"
"	font: 13pt \"Helvetica\";\n"
"}\n"
"\n"
"QLabel {\n"
"	color: #F9F9F9;\n"
"}\n"
"\n"
"QLabel#t_titel{\n"
"	font: bold\n"
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
"    background-color: #1A252E;\n"
"}")
        self.horizontalLayout = QHBoxLayout(Road_List_Item)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.t_titel = QLabel(Road_List_Item)
        self.t_titel.setObjectName(u"t_titel")

        self.horizontalLayout.addWidget(self.t_titel)

        self.i_road = QLabel(Road_List_Item)
        self.i_road.setObjectName(u"i_road")
        self.i_road.setPixmap(QPixmap(u":/icons/icons/add_road.svg"))
        self.i_road.setWordWrap(False)

        self.horizontalLayout.addWidget(self.i_road)

        self.t_pos = QLabel(Road_List_Item)
        self.t_pos.setObjectName(u"t_pos")

        self.horizontalLayout.addWidget(self.t_pos)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.b_edit = QToolButton(Road_List_Item)
        self.b_edit.setObjectName(u"b_edit")
        self.b_edit.setMinimumSize(QSize(32, 32))
        self.b_edit.setMaximumSize(QSize(32, 32))
        icon = QIcon()
        icon.addFile(u":/icons/icons/edit.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_edit.setIcon(icon)

        self.horizontalLayout.addWidget(self.b_edit)


        self.retranslateUi(Road_List_Item)

        QMetaObject.connectSlotsByName(Road_List_Item)
    # setupUi

    def retranslateUi(self, Road_List_Item):
        Road_List_Item.setWindowTitle(QCoreApplication.translate("Road_List_Item", u"Form", None))
        self.t_titel.setText(QCoreApplication.translate("Road_List_Item", u"R1", None))
        self.i_road.setText("")
        self.t_pos.setText(QCoreApplication.translate("Road_List_Item", u"x = 5", None))
        self.b_edit.setText(QCoreApplication.translate("Road_List_Item", u"...", None))
    # retranslateUi

