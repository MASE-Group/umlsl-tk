# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'query_list_item.ui'
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

class Ui_Query_List_Item(object):
    def setupUi(self, Query_List_Item):
        if not Query_List_Item.objectName():
            Query_List_Item.setObjectName(u"Query_List_Item")
        Query_List_Item.resize(506, 56)
        Query_List_Item.setStyleSheet(u"QWidget{\n"
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
        self.horizontalLayout = QHBoxLayout(Query_List_Item)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.t_titel = QLabel(Query_List_Item)
        self.t_titel.setObjectName(u"t_titel")

        self.horizontalLayout.addWidget(self.t_titel)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.b_edit = QToolButton(Query_List_Item)
        self.b_edit.setObjectName(u"b_edit")
        self.b_edit.setMinimumSize(QSize(32, 32))
        self.b_edit.setMaximumSize(QSize(32, 32))
        icon = QIcon()
        icon.addFile(u":/icons/icons/edit.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_edit.setIcon(icon)

        self.horizontalLayout.addWidget(self.b_edit)


        self.retranslateUi(Query_List_Item)

        QMetaObject.connectSlotsByName(Query_List_Item)
    # setupUi

    def retranslateUi(self, Query_List_Item):
        Query_List_Item.setWindowTitle(QCoreApplication.translate("Query_List_Item", u"Form", None))
        self.t_titel.setText("")
        self.b_edit.setText(QCoreApplication.translate("Query_List_Item", u"...", None))
    # retranslateUi

