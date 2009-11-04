class IDomainController(object):
    """
    +----------------------------------------------------------------------+
    | TODO: document this interface                                        |
    | For now, see wsgidav.domain_controller instead                       |
    +----------------------------------------------------------------------+ 

    This class is an interface for a domain controller.
    Implementations in WsgiDAV include::
      
        wsgidav.domain_controller.WsgiDAVDomainController
        wsgidav.addons.nt_domain_controller.NTDomainController
      
    All methods must be implemented.
   
    The environ variable here is the WSGI 'environ' dictionary. It is passed to 
    all methods of the domain controller as a means for developers to pass information
    from previous middleware or server config (if required).


    Domain Controllers
    ------------------
   
    The HTTP basic and digest authentication schemes are based on the following 
    concept:
   
    Each requested relative URI can be resolved to a realm for authentication, 
    for example:
    /fac_eng/courses/ee5903/timetable.pdf -> might resolve to realm 'Engineering General'
    /fac_eng/examsolns/ee5903/thisyearssolns.pdf -> might resolve to realm 'Engineering Lecturers'
    /med_sci/courses/m500/surgery.htm -> might resolve to realm 'Medical Sciences General'
    and each realm would have a set of username and password pairs that would 
    allow access to the resource.
   
    A domain controller provides this information to the HTTPAuthenticator. 
    """
