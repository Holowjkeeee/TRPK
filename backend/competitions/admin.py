from django.contrib import admin

from .models import Application, Athlete, Category, Competition, FinalProtocol, Match, Participation, Team, TeamMembership, UserProfile

admin.site.register(UserProfile)
admin.site.register(Competition)
admin.site.register(Team)
admin.site.register(Athlete)
admin.site.register(TeamMembership)
admin.site.register(Category)
admin.site.register(Application)
admin.site.register(Participation)

admin.site.register(Match)

admin.site.register(FinalProtocol)
